#!/usr/bin/env python

import apt
import os
import argparse
import tempfile
import shutil
import sys

import setup_apt_root


def parse_options():
    parser = argparse.ArgumentParser(description="List all packages available in the repos for each arch.  Filter on substring if provided")
    parser.add_argument("--rootdir", dest="rootdir", default=None,
                        help='The directory for apt to use as a rootdir')
    parser.add_argument("--substring", dest="substring", default="",
                        help="substring to filter packages displayed")
    parser.add_argument("-u", "--update", dest="update", action='store_true', default=False,
                        help="update the cache from the server")
    parser.add_argument('--repo', dest='repo_urls', action='append', metavar=['REPO_NAME@REPO_URL'],
           help='The name for the source and the url such as ros@http://repos.ros.org/repos/building')
    parser.add_argument('--destdir', dest='dest_dir', action='store', default='.',
           help='What directory to download the debs into. Default: "." ')

    args = parser.parse_args()

    # default for now to use our devel server
    if not args.repo_urls:
        args.repo_urls = ['ros@http://repos.ros.org/repos/building']
    for a in args.repo_urls:
        if not '@' in a:
            parser.error("Invalid repo definition: %s" % a)

    try:
        os.makedirs(args.dest_dir)
    except OSError, ex:
        if ex.errno != 17:
            parser.error("Failed to make directory %s with error: %s" % (args.dest_dir, ex))

    return args


def list_packages(rootdir, update, substring):
    c = apt.Cache(rootdir=rootdir)
    c.open()

    if update:
        c.update()

    c.open()  # required to recall open after updating or you will query the old data

    packages = []
    for p in [k for k in c.keys() if args.substring in k]:
        packages.append(p)

    return packages


def get_packages(rootdir, update, substring, dest_dir='.'):
    c = apt.Cache(rootdir=rootdir)
    c.open()

    if update:
        c.update()

    c.open()  # required to recall open after updating or you will query the old data

    for p in [k for k in c.keys() if args.substring in k]:
        pack = c[p]
        v = pack.candidate  # versions[0]
        print "fetching packge", p, " for arch", v.architecture,
        # This is going to throw some nasty tracebacks but it's just for the screen printing. https://bugs.launchpad.net/ubuntu/+source/apt/+bug/684785
        v.fetch_binary(destdir=dest_dir)


def render_vertical(packages):
    all_packages = set()
    for v in packages.itervalues():
        all_packages.update(v)

    if len(all_packages) == 0:
        print "no packages found matching string"
        return

    width = max([len(p) for p in all_packages])
    pstr = "package"
    print pstr, " " * (width - len(pstr)), ":",
    for k in packages.iterkeys():
        print k, "|",
    print ''

    for p in all_packages:
        l = len(p)
        print p, " " * (width - l), ":",
        for k  in packages.iterkeys():
            if p in packages[k]:
                print 'x' * len(k), '|',
            else:
                print ' ' * len(k), '|',
        print ''


if __name__ == "__main__":
    args = parse_options()

    if args.rootdir:
        rootdir = args.rootdir
    else:
        rootdir = tempfile.mkdtemp()

    arches = ['i386', 'amd64']
    distros = ['lucid', 'natty', 'oneiric']

    ros_repos = setup_apt_root.parse_repo_args(args.repo_urls)

    packages = {}

    try:
        for d in distros:
            for a in arches:
                dist_arch = "%s_%s" % (d, a)
                specific_rootdir = os.path.join(rootdir, dist_arch)
                setup_apt_root.setup_apt_rootdir(specific_rootdir, d, a, additional_repos=ros_repos)
                print "setup rootdir %s" % specific_rootdir

                packages[dist_arch] = list_packages(specific_rootdir, update=True, substring=args.substring)

        render_vertical(packages)

        result = raw_input('Would you like to pull these debs? [y/N]')
        if result == "y" or result == "Y":  # TODO change to starting with y
            print "starts with y"
        else:
            print "doesn't start with y"
            sys.exit(0)

        for d in distros:
            for a in arches:
                dist_arch = "%s_%s" % (d, a)
                specific_rootdir = os.path.join(rootdir, dist_arch)
                setup_apt_root.setup_apt_rootdir(specific_rootdir, d, a, additional_repos=ros_repos)
                print "setup rootdir %s" % specific_rootdir

                get_packages(specific_rootdir, update=True, substring=args.substring, dest_dir=args.dest_dir)

    finally:
        if not args.rootdir:  # don't delete if it's not a tempdir
            shutil.rmtree(rootdir)
