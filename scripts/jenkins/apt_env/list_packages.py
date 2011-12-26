#!/usr/bin/env python

import apt
import os
import argparse

def parse_options():
    parser = argparse.ArgumentParser(description="List all packages available in the repos.  Filter on substring if provided")
    parser.add_argument(dest="rootdir",
                        help='The directory for apt to use as a rootdir')
    parser.add_argument("--substring", dest="substring", default="", 
                        help="substring to filter packages displayed")
    parser.add_argument("-u", "--update", dest="update", action='store_true', default=False, 
                        help="update the cache from the server")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_options()

    c = apt.Cache(rootdir=args.rootdir)
    if args.update:
        c.update()

    c.open() # required to recall open after updating or you will query the old data

    for p in [k for k in c.keys() if args.substring in k]:
        v = c[p].versions[0]
        print p, v.version, v.origins


