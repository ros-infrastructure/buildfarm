#!/usr/bin/env python

import apt
import os
import argparse
import tempfile
import shutil

import setup_apt_root

def parse_options():
    parser = argparse.ArgumentParser(description="List all packages available in the repos for each arch.  Filter on substring if provided")
    parser.add_argument("--rootdir", dest="rootdir", default = None,
                        help='The directory for apt to use as a rootdir')
    parser.add_argument("--substring", dest="substring", default="", 
                        help="substring to filter packages displayed")
    parser.add_argument("-u", "--update", dest="update", action='store_true', default=False, 
                        help="update the cache from the server")
    return parser.parse_args()

def list_packages(rootdir, update, substring):
    c = apt.Cache(rootdir=rootdir)
    if update:
        c.update()

    c.open() # required to recall open after updating or you will query the old data

    packages = []
    for p in [k for k in c.keys() if args.substring in k]:
        v = c[p].versions[0]
        packages.append(p)

    return packages



if __name__ == "__main__":
    args = parse_options()


    if args.rootdir:
        rootdir = args.rootdir
    else:  
        rootdir = tempfile.mkdtemp()
        
    arches = ['i386', 'amd64']
    distros = ['lucid', 'natty', 'oneiric']


    ros_repos = [('http://50.28.27.175/repos/building', 'ros')]

    packages = {}

    try:
        for d in distros:
            for a in arches:
                dist_arch = "%s_%s"%(d, a)
                specific_rootdir = os.path.join(rootdir, dist_arch)
                setup_apt_root.setup_apt_rootdir(specific_rootdir, d, a, additional_repos = ros_repos)
                print "setup rootdir %s"%specific_rootdir
                
                packages[dist_arch] = list_packages(specific_rootdir, update=True, substring=args.substring)


        for k, v in packages.iteritems():
            print k, v
                
    finally:
        shutil.rmtree(rootdir)
