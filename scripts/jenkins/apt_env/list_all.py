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
    c.open()

    if update:
        c.update()

    c.open() # required to recall open after updating or you will query the old data

    packages = []
    for p in [k for k in c.keys() if args.substring in k]:
        v = c[p].versions[0]
        packages.append(p)

    return packages


def render_vertical(packages):
    all_packages = set()
    for v in packages.itervalues():
        all_packages.update(v)

    width = max([len(p) for p in all_packages])
    pstr = "package"
    print pstr, " "*(width-len(pstr)), ":",
    for k in packages.iterkeys():
        print k, "|",
    print '' 

    for p in all_packages:
        l = len(p)
        print p, " "*(width-l), ":",
        for k  in packages.iterkeys():
            if p in packages[k]:
                print 'x'*len(k),'|', 
            else:
                print ' '*len(k),'|', 
        print ''
            

if __name__ == "__main__":
    args = parse_options()


    if args.rootdir:
        rootdir = args.rootdir
    else:  
        rootdir = tempfile.mkdtemp()
        
    arches = ['i386', 'amd64']
    distros = ['lucid', 'natty', 'oneiric']


    ros_repos = {'ros': 'http://50.28.27.175/repos/building'}

    packages = {}

    try:
        for d in distros:
            for a in arches:
                dist_arch = "%s_%s"%(d, a)
                specific_rootdir = os.path.join(rootdir, dist_arch)
                setup_apt_root.setup_apt_rootdir(specific_rootdir, d, a, additional_repos = ros_repos)
                print "setup rootdir %s"%specific_rootdir
                
                packages[dist_arch] = list_packages(specific_rootdir, update=True, substring=args.substring)

        render_vertical(packages)
                
    finally:
        if not args.rootdir: # don't delete if it's not a tempdir
            shutil.rmtree(rootdir)
