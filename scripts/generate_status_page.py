#!/usr/bin/env python

from __future__ import print_function

import argparse
import os
import sys

from buildfarm.status_page import bin_arches, build_repo_caches, get_distro_arches, render_csv, ros_repos, transform_csv_to_html


def parse_options(args=sys.argv[1:]):
    p = argparse.ArgumentParser(description='Generate the HTML page showing the package build status.')
    p.add_argument('--basedir', default='/tmp/build_status_page', help='Root directory containing ROS apt caches. This should be created using the build_caches command.')
    p.add_argument('--skip-fetch', action='store_true', help='Skip fetching the apt data.')
    p.add_argument('--skip-csv', action='store_true', help='Skip generating .csv file.')
    p.add_argument('rosdistro', default='groovy', help='The ROS distro to generate the status page for (i.e. groovy).')
    return p.parse_args(args)


if __name__ == '__main__':
    args = parse_options()

    if not args.skip_fetch:
        print('Fetching apt data (this will take some time)...')
        build_repo_caches(args.basedir, ros_repos, get_distro_arches(bin_arches, args.rosdistro))
    else:
        print('Skip fetching apt data')

    csv_file = os.path.join(args.basedir, '%s.csv' % args.rosdistro)
    if not args.skip_csv:
        print('Generating .csv file...')
        render_csv(args.basedir, csv_file, args.rosdistro)
    elif not os.path.exists(csv_file):
        print('.csv file "%s" is missing. Call script without "--skip-csv".' % csv_file, file=sys.stderr)
    else:
        print('Skip generating .csv file')

    print('Transforming .csv into .html file...')
    with open(csv_file, 'r') as f:
        html = transform_csv_to_html(f)
    html_file = os.path.join(args.basedir, '%s.html' % args.rosdistro)
    with open(html_file, 'w') as f:
        f.write(html)

    print('Generated .html file "%s"' % html_file)
