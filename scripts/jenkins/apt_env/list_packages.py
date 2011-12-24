#!/usr/bin/env python

import apt
import os
import argparse

def parse_options():
    parser = argparse.ArgumentParser(description="List all packages available in the repo.  Filter on substring if provided")
    parser.add_argument(dest="rootdir",
                        help='The directory for apt to use as a rootdir')
    parser.add_argument("--substring", dest="substring", default="ros-", 
                        help="substring to filter packages displayed")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_options()

    c = apt.Cache(rootdir=args.rootdir)
    c.open()
    c.update()

    for p in [k for k in c.keys() if args.substring in k]:
        v = c[p].versions[0]
        print p, v.version, v.origins


