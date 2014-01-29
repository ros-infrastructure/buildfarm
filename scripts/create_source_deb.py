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
Create source debs from tarballs stored in the release repo
"""

from __future__ import print_function

import os
import sys
import subprocess
import shutil
import tempfile
import yaml

import rosdeb
import rosdeb.targets
from rosdeb.rosutil import checkout_svn_to_tmp, send_email

NAME = 'create_source_deb.py'
TARBALL_URL = "https://ros-dry-releases.googlecode.com/svn/download/stacks/%(stack_name)s/%(base_name)s/%(f_name)s"


def download_tarball(stack_name, stack_version, staging_dir):
    import urllib
    base_name = "%s-%s" % (stack_name, stack_version)
    for ext in ['tar.bz2', 'yaml']:
        f_name = "%s-%s.%s" % (stack_name, stack_version, ext)
        dest = os.path.join(staging_dir, f_name)
        url = TARBALL_URL % locals()
        urllib.urlretrieve(url, dest)


def copy_tarball_to_dir(tarball_file, staging_dir, stack_name, stack_version):
    raise Exception("not implemented")

    old_dir = os.path.abspath(os.path.dirname(tarball_file))
    new_dir = os.path.abspath(staging_dir)

    if not tarball_file.endswith('.tar.bz2'):
        raise Exception("tarball must be .tar.bz2")

    f_name = "%s-%s.tar.bz2" % (stack_name, stack_version)
    dest = os.path.join(staging_dir, f_name)
    if old_dir == new_dir:
        if os.path.basename(tarball_file) != f_name:
            # rename
            print("renaming\n  %s\n\t=>\n  %s" % (tarball_file, dest))
            os.rename(tarball_file, dest)
    else:
        print("copying\n  %s\n\t=>\n  %s" % (tarball_file, dest))
        shutil.copyfile(tarball_file, dest)


def upload_files(files, stack_name, stack_version):
    base_name = "%s-%s" % (stack_name, stack_version)
    f_name = ''  # set f_name to None to get directory
    tmp_dir = checkout_svn_to_tmp(base_name, TARBALL_URL % locals())
    subdir = os.path.join(tmp_dir, base_name)
    try:
        # copy files to subdir
        names = [os.path.basename(f) for f in files]
        for f, base in zip(files, names):
            to_path = os.path.join(subdir, base)
            print("copying %s to %s" % (f, to_path))
            assert os.path.exists(f)
            update = os.path.exists(to_path)
            if update:
                os.remove(to_path)
            shutil.copyfile(f, to_path)

            if not update:
                # svn add file
                subprocess.check_call(['svn', 'add', base], cwd=subdir)
        # commit the new files
        subprocess.check_call(['svn', 'ci', '-m', "source deb assets for %s-%s" % (stack_name, stack_version)]+names, cwd=subdir)

    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)


def _source_deb_main(distro_name, stack_name, stack_version, os_platform, staging_dir):
    if distro_name not in rosdeb.targets.os_platform:
        print("[%s] is not a valid distro.\nSupported distros are: %s" % (distro_name, ' '.join(rosdeb.targets.os_platform.keys())), sys.stderr)
        sys.exit(1)

    target_platforms = rosdeb.targets.os_platform[distro_name]
    if os_platform not in target_platforms:
        print("[%s] is not a known platform.\nSupported platforms are: %s" % (os_platform, ' '.join(target_platforms)), sys.stderr)
        sys.exit(1)

    if not os.path.exists(staging_dir):
        print("creating staging dir: %s" % (staging_dir))
        os.makedirs(staging_dir)

    download_tarball(stack_name, stack_version, staging_dir)

    # CREATE THE SOURCE DEB
    files = rosdeb.make_source_deb(distro_name, stack_name, stack_version, os_platform, staging_dir)
    upload_files(files, stack_name, stack_version)


def trigger_hudson_build_debs(name, distro_name, os_platform):
    from buildfarm import jenkins_support
    import jenkins
    import urllib
    import urllib2
    jenkins_instance = jenkins_support.JenkinsConfig_to_handle(jenkins_support.load_server_config_file(jenkins_support.get_default_catkin_debs_config()))
    parameters = {
        'DISTRO_NAME': distro_name,
        'STACK_NAME': name,
        'OS_PLATFORM': os_platform,
        }
    for arch in ['i386', 'amd64']:
        parameters['ARCH'] = arch
        job_name = 'ros-%s-%s_binarydeb_%s_%s' % (distro_name, name.replace('_', '-'), os_platform, arch)
        print('triggering job: %s' % job_name)
        if not jenkins_instance.job_exists(job_name):
            raise jenkins.JenkinsException('no such job[%s]' % (job_name))
        # pass parameters to create a POST request instead of GET
        jenkins_instance.jenkins_open(urllib2.Request(jenkins_instance.build_job_url(job_name), urllib.urlencode(parameters)))

EMAIL_FROM_ADDR = 'ROS debian build system <noreply@osrfoundation.org>'


def source_deb_main():
    # COLLECT ARGS
    from optparse import OptionParser
    parser = OptionParser(usage="usage: %prog <distro> <stack> <version> [os-platform]", prog=NAME)
    parser.add_option("--hudson",
                      dest="hudson", action='store_true', default=False,
                      help="execute for Hudson-based job.")
    parser.add_option("--smtp",
                      dest="smtp", default=None,
                      help="SMTP server to use for failure emails")

    (options, args) = parser.parse_args()

    if len(args) < 3 or len(args) > 4:
        parser.error('invalid args')

    distro_name = args[0]
    stack_name = args[1]
    stack_version = args[2]

    if len(args) == 3:
        try:
            import rosdeb.targets
            targets = rosdeb.targets.os_platform[distro_name]
        except:
            parser.error("unknown distro [%s]" % (distro_name))
    else:
        targets = [args[3]]

    errors = []
    success = []

    for os_platform in targets:
        staging_dir = os.path.join(tempfile.gettempdir(), "rosdeb-%s" % (os_platform))
        if os.path.exists(staging_dir):
            shutil.rmtree(staging_dir)
        os.mkdir(staging_dir)
        try:
            _source_deb_main(distro_name, stack_name, stack_version, os_platform, staging_dir)
            success.append(os_platform)
        except Exception as e:
            errors.append((os_platform, e))

    if options.hudson:
        for os_platform in success:
            print("triggering build-debs for %s, %s, %s" % (stack_name, distro_name, os_platform))
            trigger_hudson_build_debs(stack_name, distro_name, os_platform)

    # Handle build failures:
    #  - print out failed OS platforms
    #  - send failure e-mail
    if errors:

        # create and print error message
        error_msgs = '='*80 + '\nERRORS\n' + '='*80 + '\n'

        failed_targets = [x for x, y in errors]
        error_msgs += 'Stack [%s-%s] in distro [%s] failed to build on the following OS platforms:\n%s\n\n' % (stack_name, stack_version, distro_name, failed_targets)

        for os_platform, e in errors:
            error_msgs += '[%s]: %s\n' % (os_platform, str(e))

        error_msgs += '='*80 + '\n'

        print(error_msgs, file=sys.stderr)

        # load the control data
        control_file = os.path.join(staging_dir, "%s-%s.yaml" % (stack_name, stack_version))
        with open(control_file) as f:
            control = yaml.load(f)

        # Send e-mail for failed platforms if smtp server name is provided
        if options.smtp and 'contact' in control:
            to_addr = control['contact']
            email_msg = error_msgs
            if success:
                email_msg = 'Stack [%s-%s] in distro [%s] succeeded on the following OS platforms:\n%s\n\n' % (stack_name, stack_version, distro_name, success) + email_msg
            email_msg = """Stack [%s-%s]

There were failures in building the source deb package for this stack.
These failures are generally caused by missing dependencies on target
platforms.  If this stack is not expected to work on all target
platforms, you may be able to disregard this e-mail.

This e-mail is sent regardless of current 'excludes' settings to
assist stack maintainers who are attempting to test compatibility on
new targets.

""" % (stack_name, stack_version) + email_msg

            if set(targets) == set(failed_targets):
                subject = 'source debian build [%s-%s] failed on all platforms' % (stack_name, stack_version)
            else:
                subject = 'source debian build [%s-%s] failed on %s' % (stack_name, stack_version, ', '.join(failed_targets))

            send_email(options.smtp, EMAIL_FROM_ADDR, to_addr, subject, email_msg)
        elif not 'contact' in control:
            print("no contact e-mail in control file, will not send e-mail to owner", file=sys.stderr)
        elif not options.smtp:
            print("no SMTP server configured, will not send e-mail to owner", file=sys.stderr)

        # Exit with error code to signal build failure
        sys.exit(2)

if __name__ == '__main__':
    source_deb_main()
