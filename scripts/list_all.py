#!/usr/bin/env python

import apt
import os
import argparse
import tempfile
import shutil
import yaml
import urllib2

import buildfarm.apt_root #setup_apt_root
import buildfarm.rosdistro

import rospkg.distro

def parse_options():
    parser = argparse.ArgumentParser(description="List all packages available in the repos for each arch.  Filter on substring if provided")
    parser.add_argument("--rootdir", dest="rootdir", default = None,
                        help='The directory for apt to use as a rootdir')
    parser.add_argument("--rosdistro", dest='rosdistro', default = 'fuerte',
           help='The ros distro. electric, fuerte, groovy')
    parser.add_argument("--substring", dest="substring", default="", 
                        help="substring to filter packages displayed default = 'ros-ROSDISTRO'")
    parser.add_argument("-O", "--outfile", dest="outfile", default=None, 
                        help="File to write out to.")
    parser.add_argument("-u", "--update", dest="update", action='store_true', default=False, 
                        help="update the cache from the server")
    parser.add_argument('--repo', dest='repo_urls', action='append',metavar=['REPO_NAME@REPO_URL'],
           help='The name for the source and the url such as ros@http://50.28.27.175/repos/building')

    args = parser.parse_args()

    # default for now to use our devel server
    if not args.repo_urls:
        args.repo_urls =['ros@http://50.28.27.175/repos/building']
    for a in args.repo_urls:
        if not '@' in a:
            parser.error("Invalid repo definition: %s"%a)

    if not args.substring:
        args.substring = 'ros-%s'%args.rosdistro

    return args

class Package(object):
    def __init__(self, name, version):
        self.name = name
        self.version = version


def list_packages(rootdir, update, substring):
    c = apt.Cache(rootdir=rootdir)
    c.open()

    if update:
        c.update()

    c.open() # required to recall open after updating or you will query the old data

    packages = []
    for p in [k for k in c.keys() if args.substring in k]:
        v = c[p].versions[0]
        packages.append(Package(p, c[p].candidate.version))

    return packages



def render_vertical(packages):
    outstr = ""
    all_package_names_set = set()
    package_map = {}
    for v in packages.itervalues():
        all_package_names_set.update([p.name for p in v])

    all_package_names = list(all_package_names_set)
    all_package_names.sort()
    
    if len(all_package_names) == 0:
        print "no packages found matching substring" 
        return

    width = max([len(p) for p in all_package_names])
    pstr = "package"
    outstr += pstr + " "*(width-len(pstr))+ ":"
    arch_distro_list = sorted(packages.iterkeys())
    for k in arch_distro_list:
        outstr += k+"|"
    outstr += '\n' 

    

    for p in all_package_names:
        l = len(p)
        outstr += p + " "*(width-l) + ":"
        for k  in arch_distro_list:
            pkg_name_lookup = {}
            for pkg in packages[k]:
                pkg_name_lookup[pkg.name] = pkg
            if p in pkg_name_lookup:
                version_string = pkg_name_lookup[p].version
                outstr += version_string[:len(k)]+' '*max(0, len(k) -len(version_string) )+('|' if len(version_string) < len(k) else '>')
                #, 'x'*len(k),'|', 
            else:
                outstr+= ' '*len(k)+'|'
        outstr += '\n'
            

    outstr += "Totals" + " "*(width - len("Totals")) + ":"
    for k in arch_distro_list:
        pkg_name_lookup = {}
        for pkg in packages[k]:
            pkg_name_lookup[pkg.name] = pkg
        count_string = str(len(pkg_name_lookup.keys()))
        outstr += count_string[:len(k)]+' '*max(0, len(k) -len(count_string) )+('|' if len(count_string) < len(k) else '>')

    return outstr

if __name__ == "__main__":
    args = parse_options()


    if args.rootdir:
        # TODO: resolve rootdir to an absolute path
        rootdir = args.rootdir
    else:  
        rootdir = tempfile.mkdtemp()
        

    arches = ['i386', 'amd64']
    distros = buildfarm.rosdistro.get_target_distros(args.rosdistro)


    ros_repos = buildfarm.apt_root.parse_repo_args(args.repo_urls)

    packages = {}



    try:
        for d in distros:
            for a in arches:
                dist_arch = "%s_%s"%(d, a)
                specific_rootdir = os.path.join(rootdir, dist_arch)
                buildfarm.apt_root.setup_apt_rootdir(specific_rootdir, d, a, additional_repos = ros_repos)
                print "setup rootdir %s"%specific_rootdir
                
                packages[dist_arch] = list_packages(specific_rootdir, update=args.update, substring=args.substring)

                
    finally:
        if not args.rootdir: # don't delete if it's not a tempdir
            shutil.rmtree(rootdir)

    rd = buildfarm.rosdistro.Rosdistro(args.rosdistro)
    distro_packages = rd.get_package_list()

    wet_stacks = [Package(buildfarm.rosdistro.debianize_package_name(args.rosdistro, p), rd.get_version(p)) for p in distro_packages]

    dry_distro = rospkg.distro.load_distro(rospkg.distro.distro_uri(args.rosdistro))
    
    
    dry_stacks = [Package(buildfarm.rosdistro.debianize_package_name(args.rosdistro, sn), dry_distro.released_stacks[sn].version) for sn in dry_distro.released_stacks]

    packages[' '+ args.rosdistro] = wet_stacks + dry_stacks


    outstr = render_vertical(packages)
    print outstr


    if args.outfile:
        with open(args.outfile, 'w') as of:
            of.write(outstr + '\n')
            print "Wrote output to file %s" % args.outfile
