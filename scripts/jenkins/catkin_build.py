#!/usr/bin/env python

from __future__ import print_function
import os, sys
import subprocess
from subprocess import Popen, CalledProcessError
import re
import tempfile

import rosdistro

def parse_options():
    import argparse
    parser = argparse.ArgumentParser(description='Creates a set of source debs from a catkin gbp repo. Creates source debs from the latest upstream version.')
    parser.add_argument(dest='repo_uri',
            help='A read-only git buildpackage repo uri.')
    parser.add_argument('package_name', help='The package name for the package we\'re building')
    parser.add_argument('rosdistro', help='Which rosdistro to operate on')
    parser.add_argument('short_package_name', help='The package name for the package we\'re building, w/o the debian extensions')
    parser.add_argument('--working', help='A scratch build path. Default: %(default)s', default='/tmp/catkin_gbp')
    parser.add_argument('--output', help='The result of source deb building will go here. Default: %(default)s', default='/tmp/catkin_debs')
    parser.add_argument('--repo-fqdn', dest='repo_fqdn', help='The fully qualified domain name of the repo machine. Default: %(default)s', default='50.28.27.175')
    parser.add_argument('--repo-path', dest='repo_path', help='The path to find the repo on the machine. Default: %(default)s', default='/var/www/repos/building')
    
    args = parser.parse_args()

    return args

def make_working(working_dir):
    if not os.path.exists(working_dir):
        os.makedirs(working_dir)

def call(working_dir, command, pipe=None):
    print('+ cd %s && ' % working_dir + ' '.join(command))
    process = Popen(command, stdout=pipe, stderr=pipe, cwd=working_dir)
    output, unused_err = process.communicate()
    retcode = process.poll()
    if retcode:
        raise CalledProcessError(retcode, command)
    if pipe:
        return output

def check_local_repo_exists(repo_path):
    return os.path.exists(os.path.join(repo_path, '.git'))

def update_repo(working_dir, repo_path, repo_uri):
    if check_local_repo_exists(repo_path):
        print(repo_path)
        command = ('git', 'fetch', '--all')
        call(repo_path, command)
    else:
        command = ('gbp-clone', repo_uri)
        call(working_dir, command)

def list_debian_tags(repo_path, package_name, package_version):
    tags = call(repo_path, ('git', 'tag', '-l', 'debian/*'), pipe=subprocess.PIPE)
    print(tags, end='')
    marked_tags = []
    print ("tags", tags )
    for tag in tags.split('\n'):
        #TODO make this regex better...
        regex_str = 'debian/%s_%s_.+'%(package_name, package_version)
        m = re.search(regex_str, tag)
        if m:
            marked_tags.append(tag)
    if not marked_tags:
        print("No matching tag found. Are you sure you pointed to the right repository or the version is right?, regex %s:\n Tags: %s"%(regex_str, tags))
    return marked_tags

def build_source_deb(repo_path, tag, output):
    call(repo_path, ('git', 'checkout', tag))
    call(repo_path, ('git', 'buildpackage', '--git-export-dir=%s' % output,
        '--git-ignore-new', '-S', '-uc', '-us'))

def upload_source_deb(distro, repo_fqdn, repo_path, changes_arg):
    
    config_string = """
[uploadhost]
method                  = scp
fqdn                    = %(repo_fqdn)s
incoming                = %(repo_path)s/queue/%(distro)s
run_dinstall            = 0
post_upload_command     = ssh rosbuild@%(repo_fqdn)s -- /usr/bin/reprepro -b %(repo_path)s --ignore=emptyfilenamepart -V processincoming %(distro)s"""%locals()
    cf = tempfile.NamedTemporaryFile(delete=False)
    print("Writing config string:[%s]"%config_string)
    cf.write(config_string)
    cf.close()
    try:
        call('/tmp/', ['cat', cf.name])
        call('/tmp/', ['dput', '-u', '-c', cf.name, 'uploadhost', changes_arg])
    finally:
        os.remove(cf.name)


if __name__ == "__main__":
    args = parse_options()
    make_working(args.working)

    rd = rosdistro.Rosdistro(args.rosdistro)

    package_version = rd.get_version(args.short_package_name)
    print ("package name", args.short_package_name, "version", package_version)

    repo_base, extension = os.path.splitext(os.path.basename(args.repo_uri))
    repo_path = os.path.join(args.working, repo_base)

    update_repo(working_dir=args.working, repo_path=repo_path, repo_uri=args.repo_uri)
    tags = list_debian_tags(repo_path, args.package_name, package_version)
    if not tags:
        print("No tags; bailing")
        sys.exit(1)

    report_failure = False
    for tag in tags:
        try:
            build_source_deb(repo_path, tag, args.output)
            print("successfully created sourcedeb for tag %s on repo %s."%(tag, repo_path))
        except CalledProcessError, ex:
            print("Failed to build source deb for tag %s on repo %s: %s"%(tag, repo_path, ex))
            report_failure = True
            
    for d in rd.get_target_distros():
        try:
            upload_source_deb(d, args.repo_fqdn, args.repo_path, 
                              os.path.join(args.output, 
                                           '*'+d+'*.changes')
                              )
            print("Succeeded uploading for distro %s: %s"%(d, ex))
        except CalledProcessError, ex:
            print("Failed uploading for distro %s: %s"%(d, ex))
            report_failure = True

    if report_failure:
        print("Errors have occurred in the source build see above. ")
        sys.exit(1)
