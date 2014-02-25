#!/usr/bin/env python

from __future__ import print_function

import argparse
import os
import sys
import time

from buildfarm.compare_page import generate_html
from rosdistro import get_index, get_index_url


def parse_options(args=sys.argv[1:]):
    p = argparse.ArgumentParser(description='Generate the HTML page'
                                ' comparing the repository versions across distros.')
    p.add_argument('--basedir', default='/tmp/build_compare_page',
                   help='Root directory containing generated files.')
    p.add_argument('--resources', default='.',
                   help='Path to resources (e.g. css and js files).')
    p.add_argument('rosdistros', nargs='*', default=[],
                   help='The ROS distros to generate the compare page'
                   ' for (i.e. groovy hydro indigo).')
    return p.parse_args(args)


if __name__ == '__main__':
    args = parse_options()

    start_time = time.localtime()

    index = get_index(get_index_url())

    if not args.rosdistros:
        args.rosdistros = sorted(index.distributions.keys())
    else:
        for distro in args.rosdistros:
            assert distro in index.distributions.keys()

    if not os.path.exists(args.basedir):
      os.makedirs(args.basedir)

    html_file = os.path.join(args.basedir, 'compare_%s.html' % '_'.join(args.rosdistros))
    print("Generating '%s' file..." % html_file)
    template_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'resources', 'compare_page.html.em')
    html = generate_html(index, args.rosdistros, start_time, template_file, args.resources)
    with open(html_file, 'w') as f:
        f.write(html)

    print('Symlinking js and css...')
    for res in ['js', 'css']:
        dst = os.path.join(args.basedir, res)
        if not os.path.exists(dst):
            src = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               'resources', res)
            os.symlink(os.path.abspath(src), dst)

    print('Generated .html file "%s"' % html_file)
