#!/usr/bin/env python

from __future__ import print_function

import argparse
import os
import sys
import time

from buildfarm.status_page import build_version_cache,\
    get_distro_arches, render_csv, transform_csv_to_html


def parse_options(args=sys.argv[1:]):
    p = argparse.ArgumentParser(description='Generate the HTML page'
                                ' showing the package build status.')
    p.add_argument('--basedir', default='/tmp/build_status_page',
                   help='Root directory containing ROS apt caches.'
                   ' This should be created using the build_caches command.')
    p.add_argument('--skip-fetch', action='store_true',
                   help='Skip fetching the apt data.')
    p.add_argument('--skip-csv', action='store_true',
                   help='Skip generating .csv file.')
    p.add_argument('rosdistro', default='groovy',
                   help='The ROS distro to generate the status page'
                   ' for (i.e. groovy).')
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
          default=['i386', 'amd64'],
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
        distro_arches = [tuple(a.split(',')) for a in args.da]
    elif args.distros:
        distro_arches = [(d, a) for d in args.distros for a in args.arches]
    else:
        distro_arches = get_distro_arches(args.arches, args.rosdistro)

    version_cache = build_version_cache(args.basedir, args.rosdistro,
                                        distro_arches, ros_repos,
                                        update=not args.skip_fetch)

    csv_file = os.path.join(args.basedir, '%s.csv' % args.rosdistro)
    if not args.skip_csv:
        print('Generating .csv file...')
        render_csv(version_cache, args.basedir, csv_file, args.rosdistro,
                   distro_arches, ros_repos)
    elif not os.path.exists(csv_file):
        print('.csv file "%s" is missing. Call script without "--skip-csv".' %\
                  csv_file, file=sys.stderr)
    else:
        print('Skip generating .csv file')

    def metadata_builder(column_data):
        build_argstring = column_data.split('_')
        is_source = len(build_argstring) == 3
        distro = build_argstring[0]
        arch = build_argstring[1]
        data = {
            'rosdistro': args.rosdistro,
            'rosdistro_short': args.rosdistro[0].upper(),
            'distro': distro,
            'distro_short': distro[0].upper()
        }

        data['arch_short'] = {'amd64': '64',
                              'i386': '32',
                              'armel': 'armel',
                              'armhf': 'armhf'}[arch]

        if is_source:
            column_label = '{rosdistro_short}src{distro_short}{arch_short}'
            view_name = '{rosdistro_short}src'
        else:
            column_label = '{rosdistro_short}bin{distro_short}{arch_short}'
            view_name = '{rosdistro_short}bin{distro_short}{arch_short}'
        data['column_label'] = column_label.format(**data)
        data['view_url'] = 'http://jenkins.willowgarage.com:8080/view/%s/' % \
            view_name.format(**data)

        if is_source:
            job_name = 'ros-{rosdistro}-{{pkg}}_sourcedeb'
        else:
            data['arch'] = arch
            job_name = 'ros-{rosdistro}-{{pkg}}_binarydeb_{distro}_{arch}'
        data['job_url'] = ('{view_url}job/%s/' % job_name).format(**data)

        return data

    print('Transforming .csv into .html file...')
    with open(csv_file, 'r') as f:
        html = transform_csv_to_html(f, metadata_builder,
                                     args.rosdistro, start_time)
    html_file = os.path.join(args.basedir, '%s.html' % args.rosdistro)
    with open(html_file, 'w') as f:
        f.write(html)

    print('Symlinking jQuery resources...')
    dst = os.path.join(args.basedir, 'jquery')
    if not os.path.exists(dst):
        src = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                           'resources', 'jquery')
        os.symlink(src, dst)

    print('Generated .html file "%s"' % html_file)
