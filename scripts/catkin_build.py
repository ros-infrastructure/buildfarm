#!/usr/bin/env python

from __future__ import print_function
import os
import subprocess
from subprocess import Popen, CalledProcessError
import re
from catkin_release import check_local_repo_exists, call, make_working

def parse_options():
    import argparse
    parser = argparse.ArgumentParser(description='Creates a set of source debs from a catkin gbp repo. Creates source debs from the latest upstream version.')
    parser.add_argument(dest='repo_uri',
            help='A read-only git buildpackage repo uri.')
    parser.add_argument('--working', help='A scratch build path. Default: %(default)s', default='/tmp/catkin_gbp')
    parser.add_argument('--output', help='The result of source deb building will go here. Default: %(default)s', default='/tmp/catkin_debs')
    parser.add_argument(dest='rosdistro', help='The ros distro. electric, fuerte, galapagos')
    return parser.parse_args()

def update_repo(working_dir, repo_path, repo_uri):
    if check_local_repo_exists(repo_path):
        print(repo_path)
        command = ('git','fetch',)
        call(repo_path, command)
    else:
        command = ('gbp-clone', repo_uri)
        call(working_dir, command)

def list_debian_tags(repo_path):
    tags = call(repo_path, ('git', 'tag', '-l', 'debian/*'), pipe=subprocess.PIPE)
    print(tags, end='')
    marked_tags = []
    for tag in tags.split('\n'):
         m = re.search('debian/ros_(.*)_(\d.\d.\d)_(.*)', tag)
         if m:
             ros_X = m.group(1)
             version = m.group(2)
             distro = m.group(3)
             marked_tags.append((version, distro, ros_X, tag))
    marked_tags = sorted(marked_tags)
    marked_tags.reverse()
    return marked_tags

def get_latest_tags(tags, rosdistro):
    #filter by ros distro
    tags = [x for x in tags if rosdistro in x]

    #get a sorted set of version tags
    versions = sorted(list(set(zip(*tags)[0])))
    versions.reverse()

    #get grab the latest version, lexographical?
    latest = versions[0]

    #now find the set of tags that are have the version 
    latest_tags = [x for x in tags if latest in x]
    return latest_tags

def build_source_deb(repo_path, tag, version, ros_distro, distro, output):
    call(repo_path, ('git', 'checkout', tag))
    call(repo_path, ('git', 'buildpackage', '--git-export-dir=%s' % output,
        '--git-ignore-new', '-S', '-uc', '-us'))
if __name__ == "__main__":
    args = parse_options()
    make_working(args.working)

    repo_base, extension = os.path.splitext(os.path.basename(args.repo_uri))
    repo_path = os.path.join(args.working, repo_base)

    update_repo(working_dir=args.working, repo_path=repo_path, repo_uri=args.repo_uri)
    tags = list_debian_tags(repo_path)
    latest_tags = get_latest_tags(tags, args.rosdistro)
    for version, distro, ros_distro, tag in latest_tags:
        build_source_deb(repo_path, tag, version, ros_distro, distro, args.output)
