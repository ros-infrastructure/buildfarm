# Software License Agreement (BSD License)
#
# Copyright (c) 2010, Willow Garage, Inc.
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
#
# Revision $Id: __init__.py 10652 2010-08-11 22:01:37Z kwc $
from __future__ import with_statement

import os
import sys
import time
from subprocess import check_call
import hashlib

import yaml

import roslib.packages

from rosdeb.core import debianize_name

def make_source_deb(distro_name, stack_name, stack_version, os_platform_name, staging_dir):
    """
    @param os_platform_name: Name of OS platform/version, e.g. 'lucid'
    @type  os_platform_name: str
    @return: list of source-deb files
    @rtype: [str]
    """
    debian_name = 'ros-%s-%s'%(distro_name, debianize_name(stack_name))

    tmpl_d = os.path.join(roslib.packages.get_pkg_dir('rosdeb'), 'resources', 'source_deb')
    
    tarball = os.path.join(staging_dir, "%s-%s.tar.bz2"%(stack_name, stack_version))
    if not os.path.exists(tarball):
        raise Exception("tarball must be copied to staging directory first")

    # keep track of files we've copied in to modify
    files = []
    
    # make STACK/debian
    stack_d  = os.path.join(staging_dir, stack_name)
    debian_d = os.path.join(stack_d, 'debian')
    if not os.path.exists(debian_d):
        os.makedirs(debian_d)

    # Files which go into debian dir
    for f in ['rules', 'compat', 'postinst']:
        files.append( (os.path.join(tmpl_d, f), os.path.join(debian_d, f)) )

    # Files which go into stack dir
    for f in ['fixpc.py', 'fixbinpath.py', 'fixrpath.py', 'Makefile', 'setup_deb.sh', 'purge_build.py', 'update_version.py', 'gen_versioned_debs.py']:
        files.append( (os.path.join(tmpl_d, f), os.path.join(stack_d, f)) )
        
    # Files which go into stack dir and are different for ros stack
    if stack_name == 'ros':
        for f in ['setup_deb.sh', 'Makefile']:
            f_src = f+'-ros'
            files.append( (os.path.join(tmpl_d, f_src), os.path.join(stack_d, f)) )
                      
    # Files which go into stack dir and only exist for ros
    if stack_name == 'ros':
        for f in ['setup.sh','setup.bash','setup.zsh','.rosinstall']:
            files.append( (os.path.join(tmpl_d, f), os.path.join(stack_d, f)))

    for src, dst in files:
        with open(src, 'r') as f:
            src_text = f.read()

        dst_text = src_text.replace('${ROS_DISTRO_NAME}', distro_name)
        dst_text = dst_text.replace('${ROS_STACK_NAME}', stack_name)
        dst_text = dst_text.replace('${ROS_STACK_DEBIAN_NAME}', debian_name)
        dst_text = dst_text.replace('${ROS_STACK_VERSION}', stack_version)
        with open(dst, 'w') as f:
            f.write(dst_text)

        # copy permission modes
        s = os.stat(src)
        os.chmod(dst, s.st_mode)
            
    # CONTROL: read in the control YAML data and convert it to an actual control file
    control_yaml = os.path.join(staging_dir, '%s-%s.yaml'%(stack_name, stack_version))
    with open(control_yaml, 'r') as f:
        metadata = yaml.load(f.read())
    if not type(metadata) == dict:
        raise Exception("invalid control file: %s\nMetadata is [%s]"%(control_yaml, metadata))

    # make distro-specific
    metadata['package'] = debian_name
    with open(os.path.join(debian_d, 'control'), 'w') as f:
        f.write(control_file(metadata, distro_name, os_platform_name).encode('utf-8'))

    # CHANGELOG
    with open(os.path.join(debian_d, 'changelog'), 'w') as f:
        f.write(changelog_file(metadata, os_platform_name).encode('utf-8'))

    # We must use a build-version starting with a letter greater than r
    build_version='s$BUILD_VERSION'

    with open(os.path.join(debian_d, 'changelog.tmp'), 'w') as f:
        f.write(changelog_file(metadata, os_platform_name, build_version))
    
    # MD5Sum of original stack tar.bz2:
    with open(os.path.join(stack_d, '%s-%s.md5'%(stack_name, stack_version)),'w') as mf:
        with open(os.path.join(staging_dir, '%s-%s.tar.bz2'%(stack_name, stack_version)),'r') as f:
            m = hashlib.md5()
            m.update(f.read())
            mf.write('%s  %s\n'%(m.hexdigest(), '../%s-%s.tar.bz2'%(stack_name, stack_version)))

    # Note: this creates 3 files.  A .dsc, a .tar.gz, and a .changes
    check_call(['dpkg-buildpackage', '-S', '-uc', '-us'], cwd=stack_d)


    # SOURCE DEB: .dsc plus tarball of debian dir. Ignore the changes for now
    f_name  = "%s_%s-0~%s"%(debian_name, stack_version, os_platform_name)
    files = [os.path.join(staging_dir, f_name+ext) for ext in ('.dsc', '.tar.gz')]
    for f in files:
        assert os.path.exists(f), "File: %s does not exist"%f

    return files
    
def supported_platforms(control):
    return [version for version in control['rosdeps'].keys()]
    
def changelog_file(metadata, platform='lucid', build_version='0'):
    data = metadata.copy()
    #day-of-week, dd month yyyy hh:mm:ss +zzzz
    data['date'] = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())
    data['platform'] = platform
    data['supported'] = platform
    data['build-version'] = build_version
    
    return """%(package)s (%(version)s-%(build-version)s~%(platform)s) %(supported)s; urgency=low

  * Please see https://ros.org/wiki/%(stack)s/ChangeList
\t
 -- See website <ros-users@code.ros.org>  %(date)s
\t
"""%data
    
def deb_depends(metadata, distro_name, platform_name):
    """
    @return: list of debian package dependencies, or None if not supported on that platform
    @rtype: [str]
    """
    # if a control file does not specify deb depends for the platform, it is not valid on that platform
    if 'rosdeps' not in metadata:
        return None
    if platform_name not in metadata['rosdeps']:
        # hack to get around bug in ubuntu_map that polluted control files with bad maverick keys
        if platform_name == 'maverick' and 'mighty' in metadata['rosdeps']:
            platform_name = 'mighty'
        else:
            return None      
    rosdeps = metadata['rosdeps'][platform_name]
    # support version-locking syntax
    rosdeps_fixed = []
    for r in rosdeps:
        if '=' in r:
            # example libeigen3-dev=3.0.1-1+ros4~lucid
            if '*' in r:
                raise Exception("cannot include glob patterns in debian control file")
            rosdep_name, version = r.split('=')
            rosdeps_fixed.append("%s (=%s)"%(rosdep_name, version))
        else:
            rosdeps_fixed.append(r)
    return rosdeps_fixed

def stack_depends(metadata, distro_name, platform_name):
    """
    @return: list of debian stack dependencies
    @rtype: [str]
    """
    stackdeps = metadata.get('depends', [])
    stackdeps = ['ros-%s-%s'%(distro_name, debianize_name(s)) for s in stackdeps]

    return stackdeps
        
def download_control(stack_name, stack_version):
    url = 'https://code.ros.org/svn/release/download/stacks/%(stack_name)s/%(stack_name)s-%(stack_version)s/%(stack_name)s-%(stack_version)s.yaml'
    url = url%locals()
    import urllib2
    try:
        return yaml.load(urllib2.urlopen(url))
    except:
        raise Exception("Problem fetching yaml info for %s %s (% s).\nThis yaml info is usually created when a release is uploaded. If it is missing, either the stack version is wrong, or the release did not occur correctly."%(stack_name, stack_version, url))

def control_file(metadata, distro_name, platform_name):
    data = metadata.copy()
    data['description-full'] = metadata['description-full'].rstrip()
    data['distro_name'] = distro_name
    if data['maintainer'].startswith('Maintained by '):
        data['maintainer'] = data['maintainer'][len('Maintained by '):]

    try:
        depends = deb_depends(metadata, distro_name, platform_name)
        stacks = stack_depends(metadata, distro_name, platform_name)
        if depends is None:
            raise Exception("stack [%s] does not have valid debian package dependencies for release [%s]"%(metadata['stack'], platform_name))
        data['all-depends'] = ', '.join(depends + stacks)
        data['deb-depends'] = ', '.join(depends)
    except KeyError:
        raise Exception("stack [%s] does not have rosdeps for release [%s]"%(metadata['stack'], platform_name))
    
    return """Source: %(package)s
Section: unknown
Priority: %(priority)s
Maintainer: %(maintainer)s
Build-Depends: debhelper (>= 5), chrpath, %(all-depends)s
Standards-Version: 3.7.2
XBC-WG-rosdistro: %(distro_name)s

Package: %(package)s
Architecture: any
Depends: ${shlibs:Depends}, ${misc:Depends}, ${rosstack:Depends}, %(deb-depends)s
Description: %(description-brief)s
%(description-full)s
"""%data
