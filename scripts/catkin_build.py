#!/usr/bin/env python

from __future__ import print_function
import os
import subprocess
from subprocess import Popen, CalledProcessError
import re

def parse_options():
    import argparse
    parser = argparse.ArgumentParser(description='Creates a set of source debs from a catkin gbp repo. Creates source debs from the latest upstream version.')
    parser.add_argument(dest='repo_uri',
            help='A read-only git buildpackage repo uri.')
    parser.add_argument('package_name', help='The package name for the package we\'re building')
    parser.add_argument('--working', help='A scratch build path. Default: %(default)s', default='/tmp/catkin_gbp')
    parser.add_argument('--output', help='The result of source deb building will go here. Default: %(default)s', default='/tmp/catkin_debs')
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

def list_debian_tags(repo_path, package_name):
    tags = call(repo_path, ('git', 'tag', '-l', 'debian/*'), pipe=subprocess.PIPE)
    print(tags, end='')
    marked_tags = []
    print ("tags", tags )
    for tag in tags.split('\n'):
        #TODO make this regex better...
        regex_str = 'debian/%s_(\d+\.\d+\.\d+[^_]*)_.+'%package_name
        m = re.search(regex_str, tag)
        if m:
            version = m.group(1)
            marked_tags.append((version, tag))
    if not marked_tags:
        print("No debian tags?  Are you sure you pointed to the right repository?, regex %s"%regex_str)
    return marked_tags

def version_cmp(v1, v2):
    def normalize(v):
        return [int(x) for x in v.split(".")]
    return cmp(normalize(v1), normalize(v2))

def get_latest_tags(tags,):
    #filter by ros distro
    print("All tags: %s" % tags)

    #get a sorted set of version tags
    versions = sorted(list(set(zip(*tags)[0])), cmp=version_cmp)
    versions.reverse()

    #get grab the latest version, lexographical?
    latest = versions[0]

    #now find the set of tags that are have the version
    latest_tags = [x for v, x in tags if latest == v ]
    return latest_tags

def build_source_deb(repo_path, tag, output):
    call(repo_path, ('git', 'checkout', tag))
    call(repo_path, ('git', 'buildpackage', '--git-export-dir=%s' % output,
        '--git-ignore-new', '-S', '-uc', '-us'))
if __name__ == "__main__":
    args = parse_options()
    make_working(args.working)

    repo_base, extension = os.path.splitext(os.path.basename(args.repo_uri))
    repo_path = os.path.join(args.working, repo_base)

    update_repo(working_dir=args.working, repo_path=repo_path, repo_uri=args.repo_uri)
    tags = list_debian_tags(repo_path, args.package_name)
    latest_tags = get_latest_tags(tags)
    for tag in latest_tags:
        build_source_deb(repo_path, tag, args.output)
