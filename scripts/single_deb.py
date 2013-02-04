#!/usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2009, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
Build debs for a package and all of its dependencies as necessary
"""

import paramiko
import os
import sys
import subprocess
import shutil
import tempfile
import yaml
import urllib2
import stat
import re
import time

from rospkg.distro import distro_uri, load_distro
import rosdeb
from rosdeb import debianize_name, debianize_version, rosdistro, targets, list_missing
from rosdeb.rosutil import send_email
from rosdeb.source_deb import download_control

NAME = 'build_debs.py' 
TARBALL_URL = "https://code.ros.org/svn/release/download/stacks/%(stack_name)s/%(base_name)s/%(f_name)s"

REPO_PATH ='/var/www/repos/building'
REPO_USERNAME='rosbuild'

TGZ_VERSION='dry_6'

import traceback

def repo_url(fqdn):
   return "http://%s/repos/building"%(fqdn)

class StackBuildFailure(Exception):

    def __init__(self, message):
        self._message = message
    def __str__(self):
       return self._message

class BuildFailure(Exception):

    def __init__(self, message):
        self._message = message
    def __str__(self):
        return self._message

class InternalBuildFailure(Exception):

    def __init__(self, message):
        self._message = message
    def __str__(self):
        return self._message

    
def download_files(stack_name, stack_version, staging_dir, files):
    import urllib
    
    base_name = "%s-%s"%(stack_name, stack_version)

    dl_files = []

    for f_name in files:
        dest = os.path.join(staging_dir, f_name)
        url = TARBALL_URL%locals()
        urllib.urlretrieve(url, dest)
        dl_files.append(dest)

    return dl_files

def load_info(stack_name, stack_version):
    try:
        return download_control(stack_name, stack_version)
    except:
        traceback.print_exc()
        raise BuildFailure("Problem fetching yaml info for %s %s.\nThis yaml info is usually created when a release is uploaded. If it is missing, either the stack version is wrong, or the release did not occur correctly."%(stack_name, stack_version))

def compute_deps(distro, stack_name):

    seen = set()
    ordered_deps = []

    def add_stack(s):
        if s in seen:
            return
        if s not in distro.released_stacks:
            # ignore, possibly catkinized
            return
        seen.add(s)
        v = distro.released_stacks[s].version
        if not v:
            raise BuildFailure("[%s] has not been released (version-less)."%(s))
        # version-less entries are ignored
        si = load_info(s, v)
        loaded_deps = si['depends']
        for d in loaded_deps:
            try:
                add_stack(d)
            except BuildFailure as e:
                raise BuildFailure("[%s] build failure loading dependency [%s]: %s"%(s, d, e))
        ordered_deps.append((s,v))

    if stack_name == 'ALL':
        for s in distro.released_stacks.keys():
            try:
                add_stack(s)
            except BuildFailure as e:
                print "WARNING: Failed loading stack [%s] removing from ALL.  Error:\n%s"%(s, e)
                
    else:
        add_stack(stack_name)

    return ordered_deps

def create_chroot(distro, distro_name, os_platform, arch, repo_fqdn):

    distro_tgz = os.path.join('/var/cache/pbuilder', "%s-%s-%s.tgz"%(os_platform, arch, TGZ_VERSION))

    if os.path.exists(distro_tgz) and os.path.getsize(distro_tgz) > 0:  # Zero sized file left in place if last build crashed
        return

    debug("re-creating pbuilder cache")

    try:
        debug('loading ros stack info')
        ros_info = load_info('ros', distro.released_stacks['ros'].version)
        debug('loaded ros stack info: %s'%(ros_info))
    except:
        # mock in data if we are in fuerte+
        ros_info = {'rosdeps': {os_platform: []}}

    # force update of apt index
    subprocess.check_call(['sudo', 'apt-get', 'update'], stderr=subprocess.STDOUT)
    
    # Things that this build infrastructure depends on
    basedeps = ['wget', 'lsb-release', 'debhelper']
    # Deps we claimed to have needed for building ROS
    # TODO:FIXME: remove pkg-config
    basedeps += ['build-essential', 'python-yaml', 'cmake', 'subversion', 'python-setuptools', 'pkg-config']
    # Extra deps that some stacks seem to be missing
    basedeps += ['libxml2-dev', 'libtool', 'unzip']
    # For debugging
    basedeps += ['strace']

    rosdeps = ros_info['rosdeps']
    # hack due to bug in ubuntu_platform map
    if os_platform == 'maverick' and 'mighty' in rosdeps:
        rosdeps = rosdeps['mighty']
    else:
        rosdeps = rosdeps[os_platform]

    deplist = ' '.join(basedeps+rosdeps)

    debootstrap_type = 'debootstrap' # use default
    mirror = 'http://aptproxy.willowgarage.com/archive.ubuntu.com/ubuntu' # use wg mirror
    updates_mirror = "deb http://aptproxy.willowgarage.com/us.archive.ubuntu.com/ubuntu/ %s-updates main restricted universe multiverse"%(os_platform)
    if arch == 'armel':
        debootstrap_type = 'qemu-debootstrap'
        mirror = 'http://ports.ubuntu.com/ubuntu-ports/'
        updates_mirror = "deb http://ports.ubuntu.com/ubuntu-ports/ %s-updates main restricted universe multiverse"%(os_platform)
    shadow_mirror = 'deb %s %s main' % (repo_url(repo_fqdn), os_platform)
    # --othermirror uses a | as a separator
    other_mirror = '%s|%s'%(updates_mirror, shadow_mirror)
    command = ['dpkg', '-l', 'pbuilder']
    debug("pbuilder verison : [%s]"%(str(command)))
    subprocess.check_call(command, stderr=subprocess.STDOUT)

    command = ['sudo', 'pbuilder', '--create', '--distribution', os_platform, '--debootstrap', debootstrap_type, '--debootstrapopts', '--arch=%s'%arch, '--mirror', mirror, '--othermirror', other_mirror, '--basetgz', distro_tgz, '--components', 'main restricted universe multiverse', '--extrapackages', deplist]
    command.extend(['--debootstrapopts', '--keyring=/etc/apt/trusted.gpg', '--keyring', '/etc/apt/trusted.gpg'])
    debug("Setting up chroot: [%s]"%(str(command)))
    subprocess.check_call(command, stderr=subprocess.STDOUT)


def do_deb_build(distro_name, stack_name, stack_version, os_platform, arch, staging_dir, noupload, interactive, repo_fqdn):
    debug("Actually trying to build %s-%s..."%(stack_name, stack_version))

    distro_tgz = os.path.join('/var/cache/pbuilder', "%s-%s-%s.tgz"%(os_platform, arch, TGZ_VERSION))

    deb_name = "ros-%s-%s"%(distro_name, debianize_name(stack_name))
    deb_version = debianize_version(stack_version, '0', os_platform)
    ros_file = "%s-%s"%(stack_name, stack_version)
    deb_file = "%s_%s"%(deb_name, deb_version)

    conf_file = os.path.join(os.path.dirname(rosdeb.__file__),'pbuilder.conf')

    # Make sure the distro chroot exists
    if not os.path.exists(distro_tgz):
        raise InternalBuildFailure("%s does not exist."%(distro_tgz))

    # Download deb and tar.gz files:
    dsc_name = '%s.dsc'%(deb_file)
    tar_gz_name = '%s.tar.gz'%(deb_file)

    (dsc_file, tar_gz_file) = download_files(stack_name, stack_version, staging_dir, [dsc_name, tar_gz_name])

    # Create hook and results directories
    hook_dir = os.path.join(staging_dir, 'hooks')
    results_dir = os.path.join(staging_dir, 'results')
    build_dir = os.path.join(staging_dir, 'pbuilder')

    if not os.path.exists(hook_dir):
        os.makedirs(hook_dir)

    if not os.path.exists(results_dir):
        os.makedirs(results_dir)

    if not os.path.exists(build_dir):
        os.makedirs(build_dir)

    # Hook script which will download our tar.bz2 into environment
    p = os.path.join(hook_dir, 'A50fetch')
    with open(p, 'w') as f:
        f.write("""#!/bin/sh
set -o errexit
apt-get install ca-certificates -y # not in default ubuntu anymore
wget https://code.ros.org/svn/release/download/stacks/%(stack_name)s/%(stack_name)s-%(stack_version)s/%(stack_name)s-%(stack_version)s.tar.bz2 -O /tmp/buildd/%(stack_name)s-%(stack_version)s.tar.bz2
rosdep update
chown -R pbuilder /tmp/buildd/.ros
su pbuilder -c "rosdep resolve gtest"
su pbuilder -c "cp -r /tmp/buildd/.ros /tmp"
"""%locals())
        os.chmod(p, stat.S_IRWXU)


    # Hook script which makes sure we have updated our apt cache
    p = os.path.join(hook_dir, 'D50update')
    with open(p, 'w') as f:
        f.write("""#!/bin/bash
set -o errexit
apt-get update
apt-get install -y python-rosdep
rosdep init"""%locals())
        os.chmod(p, stat.S_IRWXU)

    if interactive:

        # Hook scripts to make us interactive:
        p = os.path.join(hook_dir, 'B50interactive')
        with open(p, 'w') as f:
            f.write("""#!/bin/bash
echo "Entering interactive environment.  Exit when done to continue pbuilder operation."
export ROS_DESTDIR=/tmp/buildd/%(deb_name)s-%(stack_version)s/debian/%(deb_name)s
source /tmp/buildd/%(deb_name)s-%(stack_version)s/setup_deb.sh
roscd %(stack_name)s
bash </dev/tty
echo "Resuming pbuilder"
"""%locals())
            os.chmod(p, stat.S_IRWXU)

        # Hook scripts to make us interactive:
        p = os.path.join(hook_dir, 'C50interactive')
        with open(p, 'w') as f:
            f.write("""#!/bin/bash
echo "Entering interactive environment.  Exit when done to continue pbuilder operation."
export ROS_DESTDIR=/tmp/buildd/%(deb_name)s-%(stack_version)s/debian/%(deb_name)s
source /tmp/buildd/%(deb_name)s-%(stack_version)s/setup_deb.sh
roscd %(stack_name)s
bash </dev/tty
echo "Resuming pbuilder"
"""%locals())
            os.chmod(p, stat.S_IRWXU)


    if arch == 'amd64' or arch == 'armel':
        archcmd = []
    else:
        archcmd = ['setarch', arch]

    # Actually build the deb.  This results in the deb being located in results_dir
    debug("starting pbuilder build of %s-%s"%(stack_name, stack_version))
    subprocess.check_call(archcmd+ ['sudo', 'pbuilder', '--build', '--basetgz', distro_tgz, '--configfile', conf_file, '--hookdir', hook_dir, '--buildresult', results_dir, '--binary-arch', '--buildplace', build_dir, dsc_file], stderr=subprocess.STDOUT)

    # Set up an RE to look for the debian file and find the build_version
    deb_version_wild = debianize_version(stack_version, '(\w*)', os_platform)
    deb_file_wild = "%s_%s_%s\.deb"%(deb_name, deb_version_wild, arch)
    build_version = None

    # Extract the version number we just built:
    files = os.listdir(results_dir)

    for f in files:
        M = re.match(deb_file_wild, f)
        if M:
            build_version = M.group(1)

    if not build_version:
        raise InternalBuildFailure("No deb-file generated matching template: %s"%deb_file_wild)

    deb_version_final = debianize_version(stack_version, build_version, os_platform)
    deb_file_final = "%s_%s"%(deb_name, deb_version_final)

    # Build a package db if we have to
    debug("starting package db build of %s-%s"%(stack_name, stack_version))
    subprocess.check_call(['bash', '-c', 'cd %(staging_dir)s && dpkg-scanpackages . > %(results_dir)s/Packages'%locals()])


    # Script to execute for deb verification
    # TODO: Add code to run all the unit-tests for the deb!
    verify_script = os.path.join(staging_dir, 'verify_script.sh')
    with open(verify_script, 'w') as f:
        f.write("""#!/bin/sh
set -o errexit
echo "deb file:%(staging_dir)s results/" > /etc/apt/sources.list.d/pbuild.list
apt-get update
apt-get install %(deb_name)s=%(deb_version_final)s -y --force-yes
dpkg -l %(deb_name)s
"""%locals())
        os.chmod(verify_script, stat.S_IRWXU)
            


    debug("starting verify script for %s-%s"%(stack_name, stack_version))
    subprocess.check_call(archcmd + ['sudo', 'pbuilder', '--execute', '--basetgz', distro_tgz, '--configfile', conf_file, '--bindmounts', results_dir, '--buildplace', build_dir, verify_script], stderr=subprocess.STDOUT)

    # Upload the debs to the server
    base_files = ['%s_%s.changes'%(deb_file, arch)] # , "%s_%s.deb"%(deb_file_final, arch)
    files = [os.path.join(results_dir, x) for x in base_files]
    print "Generated debian change files: %s" % files




    if not noupload:
        
        invalidate_debs(deb_name, os_platform, arch, repo_fqdn)

        if not upload_debs(files, distro_name, os_platform, arch, repo_fqdn):
            print "Upload of debs failed!!!"
            return 1
    return 0


def invalidate_debs(package, os_platform, arch, repo_fqdn):
    repo_path = REPO_PATH
#    cmd = "/usr/bin/reprepro -b %(repo_path)s -T deb -V listfilter %(os_platform)s \" ( Package (== %(package)s ), Architecture (== %(arch)s ) ) | (Architecture (== %(arch)s ), ( Depends ($ %(package)s,* ) | Depends ($ *%(package)s ) )\" "%locals()

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(repo_fqdn, username='rosbuild')

    # remove all dependencies
    cmd = "/usr/bin/reprepro -b %(repo_path)s -T deb -V removefilter %(os_platform)s \"Architecture (== %(arch)s ), Depends ($ *%(package)s[ ,]* ) | Depends ($ *%(package)s )\" "%locals()
    cmd = cmd.replace('$', '%')

    print "Invalidation command: ", cmd
    stdin, stdout, stderr = ssh.exec_command(cmd)
    print "Invalidation results:", stdout.readlines(), stderr.readlines()

    # remove the package itseif
    cmd = "/usr/bin/reprepro -b %(repo_path)s -T deb -V removefilter %(os_platform)s \"Package (== %(package)s ), Architecture (== %(arch)s ) \" "%locals()


    print "Invalidation command: ", cmd
    stdin, stdout, stderr = ssh.exec_command(cmd)
    print "Invalidation results:", stdout.readlines(), stderr.readlines()
    ssh.close()


def upload_debs(files, distro_name, os_platform, arch, repo_fqdn):
    replace_elements  = {}
    replace_elements['repo_hostname'] = repo_fqdn
    replace_elements['repo_incoming_path'] = os.path.join(REPO_PATH, 'queue', os_platform)
    replace_elements['repo_path'] = REPO_PATH
    replace_elements['distro'] = os_platform
    replace_elements['repo_username'] = REPO_USERNAME

    try:
        tf_name = None
        with tempfile.NamedTemporaryFile(delete=False)  as tf:
            tf.write("""
[debtarget]
method                  = scp
fqdn                    = %(repo_hostname)s
incoming                = %(repo_incoming_path)s
run_dinstall            = 0
post_upload_command     = ssh %(repo_username)s@%(repo_hostname)s -- /usr/bin/reprepro -b %(repo_path)s --ignore=emptyfilenamepart -V processincoming %(distro)s
""" % replace_elements)
            tf_name = tf.name

        ret_val = subprocess.call(['cat', tf_name])
        cmd = ['dput', '-u', '-c', tf_name, 'debtarget' ]
        cmd.extend(files)
        print "Uploading with command: %s" % cmd
        subprocess.check_call(cmd)
    finally:
        if tf_name:
            if os.path.exists(tf_name):
                os.remove(tf_name)

    return ret_val == 0


#    if res != 0:
#        debug("ERROR: Could not run upload script")
#        debug("ERROR: output of upload script: %s"%o)
#        return 1
#    else:
#        return 0
            
            # The cache is no longer valid, we clear it so that we won't skip debs that have been invalidated
            # ??? What was this doing?
            #rosdeb.repo._Packages_cache = {}

def upload_binary_debs(files, distro_name, os_platform, arch, repo_fqdn):

    if len(files) == 0:
        debug("No debs to upload.")
        return 1 # no files to upload

    subprocess.check_call(['scp'] + files + ['%s@%s:%s/queue/%s'%(REPO_USERNAME, repo_fqdn, REPO_PATH, os_platform)], stderr=subprocess.STDOUT)

    base_files = [x.split('/')[-1] for x in files]


    new_files = ' '.join(os.path.join('%s/queue'%(REPO_PATH),os_platform,x) for x in base_files)


    # load repo_path into locals for substitution below
    repo_path = REPO_PATH

    # This script moves files into queue directory, removes all dependent debs, removes the existing deb, and then processes the incoming files
    remote_cmd = "TMPFILE=`mktemp` || exit 1 && cat > ${TMPFILE} && chmod +x ${TMPFILE} && ${TMPFILE}; ret=${?}; rm ${TMPFILE}; exit ${ret}"
    run_script = subprocess.Popen(['ssh', "%s@%s"%(REPO_USERNAME, repo_fqdn), remote_cmd], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    script_content = """
#!/bin/bash
set -o errexit
(
flock 200
reprepro -V -b %(repo_path)s includedeb %(os_platform)s %(new_files)s
rm %(new_files)s
) 200>/var/lock/ros-shadow.lock
"""%locals()

    #Actually run script and check result
    (o,e) = run_script.communicate(script_content)
    res = run_script.wait()
    debug("result of run script: %s"%o)
    if res != 0:
        debug("ERROR: Could not run upload script")
        debug("ERROR: output of upload script: %s"%o)
        return 1
    else:
        return 0


def debug(msg):
    print "[build_debs]: %s"%(msg)
    
    
def build_debs(distro, stack_name, os_platform, arch, staging_dir, force, noupload, interactive, repo_fqdn):
    distro_name = distro.release_name

    if stack_name not in distro.released_stacks:
        raise BuildFailure("stack [%s] not found in distro [%s]."%(stack_name, distro_name))


    try:
        stack_version = distro.released_stacks[stack_name].version
    except KeyError, ex:
        debug("Stack [%s] is not in in the distro: %s" % (stack_name, ex) )

    
    broken = set()
    skipped = set()


    debug("Attempting to build: %s"%(str(stack_name)))
    #si = load_info(stack_name, stack_version)
    missing_depends = list_missing.compute_missing_depends(stack_name, distro, os_platform, arch, repo = repo_url(repo_fqdn))
    if not missing_depends:
        # Create the environment where we build the debs, if necessary
        create_chroot(distro, distro_name, os_platform, arch, repo_fqdn)
        debug("Initiating build of: %s"%(str(stack_name)))
        try:
            do_deb_build(distro_name, stack_name, stack_version, os_platform, arch, staging_dir, noupload, interactive, repo_fqdn)
        except Exception, ex:
            debug("Exception was %s" % ex)
            debug("Build of [%s] failed, adding to broken list"%(str(stack_name)))
            broken.add(stack_name)
    else:
        debug("Skipping %s (%s) since dependencies not built: %s"%(stack_name, stack_version, missing_depends))
        skipped.add(stack_name)

    if broken.union(skipped):
        raise StackBuildFailure("debbuild did not complete successfully. A list of broken and skipped stacks are below. Broken means the stack itself did not build. Skipped stacks means that the stack's dependencies could not be built.\n\nBroken stacks: %s.  Skipped stacks: %s"%(broken, skipped))

EMAIL_FROM_ADDR = 'ROS debian build system <noreply@willowgarage.com>'


def parse_deb_packages(text):
    parsed = {}
    (key,val,pkg) = (None,'',{})
    count = 0
    for l in text.split('\n'):
        count += 1
        if len(l) == 0:
            if len(pkg) > 0:
                if not 'Package' in pkg:
                    print 'INVALID at %d'%count
                else:
                    if key:
                        pkg[key] = val
                    parsed[pkg['Package']] = pkg
                    (key,val,pkg) = (None,'',{})
        elif l[0].isspace():
            val += '\n'+l.strip()
        else:
            if key:
                pkg[key] = val
            (key, val) = l.split(':',1)
            key = key.strip()
            val = val.strip()

    return parsed


def create_meta_pkg(packagelist, distro, distro_name, metapackage, deps, os_platform, arch, staging_dir, wet_distro):
    workdir = staging_dir
    metadir = os.path.join(workdir, 'meta')
    if not os.path.exists(metadir):
        os.makedirs(metadir)
    debdir = os.path.join(metadir, 'DEBIAN')
    if not os.path.exists(debdir):
        os.makedirs(debdir)
    control_file = os.path.join(debdir, 'control')

    deb_name = "ros-%s-%s"%(distro_name, debianize_name(metapackage))
    deb_version = "1.0.0-s%d~%s"%(time.mktime(time.gmtime()), os_platform)

    ros_depends = []

    missing = False




    for stack in deps:
        if stack in distro.released_stacks or wet_distro.get_package_list():
            stack_deb_name = "ros-%s-%s"%(distro_name, debianize_name(stack))
            if stack_deb_name in packagelist:
                stack_deb_version = packagelist[stack_deb_name]['Version']
                ros_depends.append('%s (= %s)'%(stack_deb_name, stack_deb_version))
            else:
                debug("WARNING: Variant %s depends on non-built deb, %s"%(metapackage, stack))
                missing = True
        else:
            debug("WARNING: Variant %s depends on non-exist stack, %s"%(metapackage, stack))
            missing = True

    if missing:
        return None

    ros_depends_str = ', '.join(ros_depends)

    with open(control_file, 'w') as f:
        f.write("""
Package: %(deb_name)s
Version: %(deb_version)s
Architecture: %(arch)s
Maintainer: The ROS community <ros-user@lists.sourceforge.net>
Installed-Size:
Depends: %(ros_depends_str)s
Section: unknown
Priority: optional
WG-rosdistro: %(distro_name)s
Description: Meta package for %(metapackage)s variant of ROS.
"""%locals())

    if not missing:
        dest_deb = os.path.join(workdir, "%(deb_name)s_%(deb_version)s_%(arch)s.deb"%locals())
        subprocess.check_call(['dpkg-deb', '--nocheck', '--build', metadir, dest_deb], stderr=subprocess.STDOUT)
    else:
        dest_deb = None

    shutil.rmtree(metadir)
    return dest_deb



def gen_metapkgs(distro, os_platform, arch, staging_dir, repo_fqdn, force=False):
    distro_name = distro.release_name

    # Retrieve the package list from the shadow repo
    packageurl=repo_url(repo_fqdn)+"/dists/%(os_platform)s/main/binary-%(arch)s/Packages"%locals()
    packagetxt = urllib2.urlopen(packageurl).read()
    packagelist = parse_deb_packages(packagetxt)

    debs = []

    missing = []

    missing_primary, missing_dep, missing_excluded, missing_excluded_dep = list_missing.get_missing(distro, os_platform, arch)

    missing_ok = missing_excluded.union(missing_excluded_dep)

    
    # if (metapkg missing) or (metapkg missing deps), then create
    # modify create to version-lock deps

    wet_distro = rosdistro.Rosdistro(distro_name)


    # Build the new meta packages
    for (v,d) in distro.variants.iteritems():

        deb_name = "ros-%s-%s"%(distro_name, debianize_name(v))

        # If the metapkg is in the packagelist AND already has the right deps, we leave it:
        if deb_name in packagelist:
            list_deps = set([x.split()[0].strip() for x in packagelist[deb_name]['Depends'].split(',')])
            mp_deps = set(["ros-%s-%s"%(distro_name, debianize_name(x)) for x in set(d.stack_names) - missing_ok])
            if list_deps == mp_deps:
                debug("Metapackage %s already has correct deps"%deb_name)
                continue

        # Else, we create the new metapkg
        mp = create_meta_pkg(packagelist, distro, distro_name, v, set(d.stack_names) - missing_ok, os_platform, arch, staging_dir, wet_distro)
        if mp:
            debs.append(mp)
        else:
            missing.append(v)

    # We should always need to build the special "all" metapackage
    mp = create_meta_pkg(packagelist, distro, distro_name, "all", set(distro.released_stacks.keys()) - missing_ok, os_platform, arch, staging_dir, wet_distro)
    if mp:
        debs.append(mp)
    else:
        missing.append('all')

    upload_binary_debs(debs, distro_name, os_platform, arch, repo_fqdn)

    if missing:
        raise StackBuildFailure("Did not generate all metapkgs: %s."%missing)


def gen_metapkgs_setup(staging_dir_arg, distro, os_platform, arch, repo_fqdn):
    if staging_dir_arg is not None:
        staging_dir    = staging_dir_arg
        staging_dir = os.path.abspath(staging_dir)
    else:
        staging_dir = tempfile.mkdtemp()

    warning_message = None
    failure_message = None

    try:
        gen_metapkgs(distro, os_platform, arch, staging_dir, repo_fqdn)
    except BuildFailure, e:
        failure_message = "Failure Message:\n"+"="*80+'\n'+str(e)
    except StackBuildFailure, e:
        warning_message = "Warning Message:\n"+"="*80+'\n'+str(e)
    except Exception, e:
        failure_message = "Internal failure in the release system. Please notify ros-release@code.ros.org:\n%s\n\n%s"%(e, traceback.format_exc(e))
    finally:
        if staging_dir is None:
            shutil.rmtree(staging_dir)

    return warning_message, failure_message


def single_deb_main():

    from optparse import OptionParser
    parser = OptionParser(usage="usage: %prog <distro> <stack> <os-platform> <arch>", prog=NAME)

    parser.add_option("-d", "--dir",
                      dest="staging_dir", default=None,
                      help="directory to use for staging source debs", metavar="STAGING_DIR")
    parser.add_option("--force",
                      dest="force", default=False, action="store_true")
    parser.add_option("--noupload",
                      dest="noupload", default=False, action="store_true")
    parser.add_option("--fqdn",
                      dest="fqdn", default='50.28.27.175', action="store")
    parser.add_option("--interactive",
                      dest="interactive", default=False, action="store_true")
    parser.add_option('--smtp', dest="smtp", default='pub1.willowgarage.com', metavar="SMTP_SERVER")

    (options, args) = parser.parse_args()

    if len(args) != 4:
        parser.error('invalid args')
        
    (distro_name, stack_name, os_platform, arch) = args
    distro = failure_message = warning_message = None

    if options.staging_dir is not None:
        staging_dir    = options.staging_dir
        staging_dir = os.path.abspath(staging_dir)
    else:
        staging_dir = tempfile.mkdtemp()


    try:
        if distro_name not in rosdeb.targets.os_platform:
            raise BuildFailure("[%s] is not a known rosdistro.\nValid rosdistros are: %s" % (distro_name, ' '.join(rosdeb.targets.os_platform.keys())))
        target_platforms = rosdeb.targets.os_platform[distro_name]
        if os_platform not in target_platforms:
            raise BuildFailure("[%s] is not a known platformfor distro %s.\nSupported platforms are: %s" % (os_platform, distro_name, ' '.join(target_platforms)))

        if not os.path.exists(staging_dir):
            debug("creating staging dir: %s"%(staging_dir))
            os.makedirs(staging_dir)

        uri = distro_uri(distro_name)
        debug("loading distro file from %s"%(uri))
        distro = load_distro(uri)

        if stack_name == 'metapackages':
            (warning_message, failure_message) = gen_metapkgs_setup(options.staging_dir, distro, os_platform, arch, options.fqdn)
        else:
            build_debs(distro, stack_name, os_platform, arch, staging_dir, options.force, options.noupload, options.interactive, options.fqdn)

    except StackBuildFailure, e:
        warning_message = "Warning Message:\n"+"="*80+'\n'+str(e)
    except BuildFailure, e:
        failure_message = "Failure Message:\n"+"="*80+'\n'+str(e)
    except Exception, e:
        failure_message = "Internal failure release system. Please notify ros-release@code.ros.org:\n%s\n\n%s"%(e, traceback.format_exc(e))
    finally:
        # if we created our own staging dir, we are responsible for cleaning it up
        if options.staging_dir is None:
            shutil.rmtree(staging_dir)


    if failure_message or warning_message:
        debug("FAILURE: %s"%failure_message)
        debug("WARNING: %s"%warning_message)

        if not options.interactive:
            failure_message = "%s\n%s\n%s"%(failure_message, warning_message, os.environ.get('BUILD_URL', ''))
            if options.smtp and stack_name != 'metapackages' and distro is not None:
                stack_version = distro.stacks[stack_name].version
                control = download_control(stack_name, stack_version)
                if  'contact' in control and distro_name != 'diamondback':
                    to_addr = control['contact']
                    subject = 'debian build [%s-%s-%s-%s] failed'%(distro_name, stack_name, os_platform, arch)
                    # DISABLE SENDING OF EMAIL from script. This can be done better by jenkins. 
                    # send_email(options.smtp, EMAIL_FROM_ADDR, to_addr, subject, failure_message)
        sys.exit(1)
            

    
if __name__ == '__main__':
    single_deb_main()

