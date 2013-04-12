#!/usr/bin/env python

import apt
import argparse
import sys


def parse_options():
    parser = argparse.ArgumentParser(description="Return 0 if all packages are found in the repository, else print missing packages and return 1.")
    parser.add_argument(dest="rootdir",
                        help='The directory for apt to use as a rootdir')
    parser.add_argument(dest="aptconffile",
                        help='The aptconffile which points to the rootdir')
    parser.add_argument(dest="packages", nargs='+',
                        help="what packages to test for.")
    parser.add_argument("-u", "--update", dest="update", action='store_true', default=False,
                        help="update the cache from the server")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_options()

    c = apt.Cache(rootdir=args.rootdir)
    if args.update:
        c.update()

    c.open()  # required to recall open after updating or you will query the old data

    for p in args.packages:
        failure = False
        if p not in c:
            print "Package %s missing in repo." % p
            failure = True

    if failure:
        sys.exit(1)
    sys.exit(0)
