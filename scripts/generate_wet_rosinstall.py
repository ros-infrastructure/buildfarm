#!/usr/bin/env python

from __future__ import print_function
import argparse
import yaml

import os
import distutils.version
import urllib2
import json
import sys

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse #py3k


URL_PROTOTYPE="https://raw.github.com/ros/rosdistro/master/releases/%s.yaml"

def parse_options():
    parser = argparse.ArgumentParser(
             description='Create a rosinstall file for the wet rosdistro.')
    parser.add_argument(dest='rosdistro',
           help='The ros distro. electric, fuerte, galapagos')
    args = parser.parse_args()
    return args


def compute_rosinstall_snippet(local_name, gbp_url, version, distro_name):

    if version is None:
        print ("Error version unset for %s"%local_name)
        return None
    config = {}
    config['local-name'] = local_name

    config['version'] = 'upstream/%s'%version
    #config['version'] = '%s-%s'%(local_name, version)
    config['uri'] = gbp_url
    return {'git': config}

import time

def timed_compute_rosinstall_snippet(local_name, gbp_url, version, distro_name):
    time.sleep(1.0)
    
    return compute_rosinstall_snippet(local_name, gbp_url, version, distro_name)

if __name__ == "__main__":
    args = parse_options()

    print("Fetching " + URL_PROTOTYPE%args.rosdistro)
    repo_map = yaml.load(urllib2.urlopen(URL_PROTOTYPE%args.rosdistro))
    if 'release-name' not in repo_map:
        print("No 'release-name' key in yaml file")
        sys.exit(1)
    if repo_map['release-name'] != args.rosdistro:
        print('release-name mismatch (%s != %s)'%(repo_map['release-name'],args.rosdistro))
        sys.exit(1)
    if 'gbp-repos' not in repo_map:
        print("No 'gbp-repos' key in yaml file")
        sys.exit(1)

    rosinstall_data = [compute_rosinstall_snippet(r['name'], r['url'], r['version'], args.rosdistro) for r in repo_map['gbp-repos'] if 'url' in r and 'name' in r]
    rosinstall_data = [x for x in rosinstall_data if x]
    print(yaml.safe_dump(rosinstall_data, default_flow_style=False))
