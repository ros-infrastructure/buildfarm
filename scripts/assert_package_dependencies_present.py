#!/usr/bin/env python

import apt
import os
import argparse
import sys
import subprocess
import shutil
import tempfile
import yaml


def parse_options():
    parser = argparse.ArgumentParser(
        description="Return 0 if all packages are found in"
        " the repository, else print missing packages and return 1.")
    parser.add_argument(dest="rootdir",
                        help='The directory for apt to use as a rootdir')
    parser.add_argument(dest="aptconffile",
                        help='The aptconffile which points to the rootdir')
    parser.add_argument(dest="packages", nargs='+',
                        help="what packages to test for.")
    parser.add_argument("-u", "--update", dest="update", action='store_true',
                        default=False, help="update the cache from the server")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_options()

    #cmd = 'apt-get update -c %s'%args.aptconffile
    #subprocess.call(cmd.split())

    c = apt.Cache(rootdir=args.rootdir)
    if args.update:
        c.update()

    # required to recall open after updating or you will query the old data
    c.open()

    missing = []
    for p in args.packages:
        tdir = tempfile.mkdtemp()
        try:
            cmd = 'apt-get source %s -c %s --dsc-only --download-only' % \
                (p, args.aptconffile)
            subprocess.check_call(cmd.split(), cwd=tdir)
            dir_list = os.listdir(tdir)
            dsc_file = None
            for entry in dir_list:
                if '.dsc' in entry:
                    dsc_file = os.path.join(tdir, entry)

            if not dsc_file:
                missing.append(p)
                print "No DSC file fetched for package %s" % p

            with open(dsc_file, 'r') as dsc:
                y = yaml.load(dsc.read())
                build_depends = y['Build-Depends'].split(',')

                for dep in [dep.strip() for dep in build_depends]:
                    dep_name_only = dep.split()[0]
                    if dep_name_only not in c:
                        print "package %s does not have dependency [%s]" % \
                            (p, dep_name_only)
                        missing.append(dep_name_only)

        except Exception as ex:
            print "Exception processing package %s: %s" % (p, ex)
            missing.append(p)
        finally:
            shutil.rmtree(tdir)

    if missing:
        print "Dependencies not satisfied for packages: %s" % missing
        sys.exit(1)
    else:
        sys.exit(0)
