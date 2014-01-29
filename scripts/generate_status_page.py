#!/usr/bin/env python

from __future__ import print_function

import argparse
import os
import sys
import time

from buildfarm.apt_data import get_version_data
from buildfarm.status_page import get_distro_arches, render_csv, transform_csv_to_html
from rosdistro import get_cached_distribution, get_index, get_index_url

JENKINS_HOST = 'http://jenkins.ros.org'


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
    p.add_argument('--resources', default='.',
                   help='Path to resources (e.g. css and js files).')
    p.add_argument('rosdistro', default='groovy',
                   help='The ROS distro to generate the status page'
                   ' for (i.e. groovy).')
    p.add_argument('--build-repo',
                   default='http://repos.ros.org/repos/building',
                   help='Repository URL for the build farm repository.')
    p.add_argument('--shadow-repo',
                   default='http://repos.ros.org/repos/ros-shadow-fixed/ubuntu/',
                   help='Repository URL for the staging repository.')
    p.add_argument('--public-repo',
                   default='http://repos.ros.org/repos/ros/ubuntu/',
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

    csv_file = os.path.join(args.basedir, '%s.csv' % args.rosdistro)
    if not args.skip_csv:
        print('Assembling apt version cache')
        rd_data, apt_data = get_version_data(args.basedir, args.rosdistro,
                                             ros_repos, distro_arches,
                                             apt_update=not args.skip_fetch)
        print('Generating .csv file...')
        render_csv(rd_data, apt_data, csv_file, args.rosdistro,
                   distro_arches, ros_repos)
    elif not os.path.exists(csv_file):
        print('.csv file "%s" is missing. Call script without "--skip-csv".' %
              csv_file, file=sys.stderr)
    else:
        print('Skip generating .csv file')

    def metadata_builder(column_data):
        build_argstring = column_data.split('_')
        distro = build_argstring[0]
        arch = build_argstring[1]
        is_source = arch == 'source'
        data = {
            'rosdistro': args.rosdistro,
            'rosdistro_short': args.rosdistro[0].upper(),
            'distro': distro,
            'distro_short': distro[0].upper(),
            'is_source': is_source
        }

        data['arch_short'] = {'amd64': '64',
                              'i386': '32',
                              'armel': 'armel',
                              'armhf': 'armhf',
                              'source': 'src'}[arch]

        if is_source:
            column_label = '{rosdistro_short}src{distro_short}'
            view_name = '{rosdistro_short}src'
        else:
            column_label = '{rosdistro_short}bin{distro_short}{arch_short}'
            view_name = '{rosdistro_short}bin{distro_short}{arch_short}'
        data['column_label'] = column_label.format(**data)
        data['view_url'] = JENKINS_HOST + '/view/%s/' % \
            view_name.format(**data)

        if is_source:
            job_name = 'ros-{rosdistro}-{{pkg}}_sourcedeb'
        else:
            data['arch'] = arch
            job_name = 'ros-{rosdistro}-{{pkg}}_binarydeb_{distro}_{arch}'
        data['job_url'] = ('{view_url}job/%s/' % job_name).format(**data)

        return data

    if args.rosdistro != 'fuerte':
        index = get_index(get_index_url())
        cached_distribution = get_cached_distribution(index, args.rosdistro)
    else:
        cached_distribution = None

    print('Transforming .csv into .html file...')
    template_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'resources', 'status_page.html.em')
    with open(csv_file, 'r') as f:
        html = transform_csv_to_html(f, metadata_builder, args.rosdistro,
                                     start_time, template_file, args.resources, cached_distribution)
    html_file = os.path.join(args.basedir, '%s.html' % args.rosdistro)
    with open(html_file, 'w') as f:
        f.write(html)  # .encode('utf8'))

    print('Symlinking js and css...')
    for res in ['js', 'css']:
        dst = os.path.join(args.basedir, res)
        if not os.path.exists(dst):
            src = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               'resources', res)
            os.symlink(os.path.abspath(src), dst)

    print('Generated .html file "%s"' % html_file)
