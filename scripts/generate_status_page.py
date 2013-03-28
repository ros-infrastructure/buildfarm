#!/usr/bin/env python

from __future__ import print_function

import argparse
import os
import sys
import time

from buildfarm.status_page import build_repo_caches, get_distro_arches, render_csv, transform_csv_to_html
import buildfarm.status_page


def parse_options(args=sys.argv[1:]):
    p = argparse.ArgumentParser(description='Generate the HTML page showing the package build status.')
    p.add_argument('--basedir', default='/tmp/build_status_page', help='Root directory containing ROS apt caches. This should be created using the build_caches command.')
    p.add_argument('--skip-fetch', action='store_true', help='Skip fetching the apt data.')
    p.add_argument('--skip-csv', action='store_true', help='Skip generating .csv file.')
    p.add_argument('rosdistro', default='groovy', help='The ROS distro to generate the status page for (i.e. groovy).')
    p.add_argument('--build-repo', 
          default='http://50.28.27.175/repos/building',
          help='Repository URL for the build farm repository.')
    p.add_argument('--shadow-repo', 
          default='http://packages.ros.org/ros-shadow-fixed/ubuntu/',
          help='Repository URL for the staging repository.')
    p.add_argument('--public-repo',
          default='http://packages.ros.org/ros/ubuntu/',
          help='Repository URL for the public repository.')
    p.add_argument('--distros',
          nargs='+',
          help='Distributions to query')
    p.add_argument('--arches',
          default=buildfarm.status_page.bin_arches,
          nargs='+',
          help='Architectures to query')
    p.add_argument('--da',
          nargs='+',
          help='Distro/Arch pairs to query')
    return p.parse_args(args)


if __name__ == '__main__':
    args = parse_options()

    start_time = time.localtime()

    ros_repos = {'ros': args.public_repo,
        'shadow-fixed': args.shadow_repo,
            'building': args.build_repo}

    distro_arches = []
    if args.da:
        distro_arches = [ tuple(a.split(',')) for a in args.da ]
    elif args.distros:
        distro_arches = [ (d, a) for d in args.distros for a in args.arches ]
    else:
        distro_arches = get_distro_arches(args.arches, args.rosdistro)

    if not args.skip_fetch:
        print('Fetching apt data (this will take some time)...')
        build_repo_caches(args.basedir, ros_repos, distro_arches)
    else:
        print('Skip fetching apt data')

    csv_file = os.path.join(args.basedir, '%s.csv' % args.rosdistro)
    if not args.skip_csv:
        print('Generating .csv file...')
        render_csv(args.basedir, csv_file, args.rosdistro, distro_arches, ros_repos)
    elif not os.path.exists(csv_file):
        print('.csv file "%s" is missing. Call script without "--skip-csv".' % csv_file, file=sys.stderr)
    else:
        print('Skip generating .csv file')

    def metadata_builder(column_data):
        distro, jobtype = column_data.split('_', 1)
        data = {
            'rosdistro': args.rosdistro,
            'rosdistro_short': args.rosdistro[0].upper(),
            'distro': distro,
            'distro_short': distro[0].upper()
        }
        is_source = jobtype == 'source'
        if is_source:
            column_label = '{rosdistro_short}src{distro_short}'
            view_name = '{rosdistro_short}src'
        else:
            data['arch_short'] = {  'amd64': '64',
                                    'i386': '32', 
                                    'armel': 'armel',
                                    'armhf': 'armhf'}[jobtype]
            column_label = '{rosdistro_short}bin{distro_short}{arch_short}'
            view_name = '{rosdistro_short}bin{distro_short}{arch_short}'
        data['column_label'] = column_label.format(**data)
        data['view_url'] = 'http://jenkins.willowgarage.com:8080/view/%s/' % view_name.format(**data)

        if is_source:
            job_name = 'ros-{rosdistro}-{{pkg}}_sourcedeb'
        else:
            data['arch'] = jobtype
            job_name = 'ros-{rosdistro}-{{pkg}}_binarydeb_{distro}_{arch}'
        data['job_url'] = ('{view_url}job/%s/' % job_name).format(**data)

        return data

    print('Transforming .csv into .html file...')
    with open(csv_file, 'r') as f:
        html = transform_csv_to_html(f, metadata_builder, args.rosdistro, start_time)
    html_file = os.path.join(args.basedir, '%s.html' % args.rosdistro)
    with open(html_file, 'w') as f:
        f.write(html)

    print('Symlinking jQuery resources...')
    dst = os.path.join(args.basedir, 'jquery')
    if not os.path.exists(dst):
        src = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'jquery')
        os.symlink(src, dst)

    print('Generated .html file "%s"' % html_file)
