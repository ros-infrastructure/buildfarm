#!/usr/bin/env python

from __future__ import print_function
import argparse
import yaml

import os
import distutils.version
import urllib2
import sys

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse #py3k

import buildfarm.rosdistro


URL_PROTOTYPE="https://raw.github.com/ros/rosdistro/master/releases/%s.yaml"

def parse_options():
    parser = argparse.ArgumentParser(
             description='Create a rosinstall file for the wet rosdistro.')
    parser.add_argument(dest='rosdistro',
           help='The ros distro. electric, fuerte, galapagos')
    parser.add_argument(dest='distro',
           help='The ubuntu distro. lucid, oneiric, precise')
    args = parser.parse_args()
    return args



import time


if __name__ == "__main__":
    args = parse_options()

    rd = buildfarm.rosdistro.Rosdistro(args.rosdistro)
    
    rosinstall_data = rd.compute_rosinstall_distro(args.rosdistro, args.distro)

    print(yaml.safe_dump(rosinstall_data, default_flow_style=False))
