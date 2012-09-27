#!/usr/bin/env python
#
# Repository status script; TODO: better description of exactly what this does 
#
# TODO:
# - Produce unified, human-readable HTML output
# - Notes from Tully:
#  - I'd like to converge on an object based repo representation, which will 
#    have all the packages, and different versions queriable
#  - There are basic helper functions in src/buildfarm/repo.py
#  - The goal would be to have a structure like the Rosdistro class 
#    (src/buildfarm/rosdistro.py), where it loads all the info in the 
#    constructor from the remote repo; then you can just query it
#
# Example invocations:
#  This is called by the build farm to generate the status pages as (abbreviated)
#  list_all.py --rootdir repocache --substring ros-fuerte -u -O fuerte_building.txt
#  list_all.py --rootdir shadow_fixed_repocache --substring ros-fuerte -u --repo shadow@http://packages.ros.org/ros-shadow-fixed/ubuntu/ -O fuerte_testing.txt
#  list_all.py --rootdir ros_repocache --substring ros-fuerte -u --repo shadow@http://packages.ros.org/ros/ubuntu/ -O fuerte_public.txt
#  scp -o StrictHostKeyChecking=no fuerte_building.txt fuerte_public.txt fuerte_testing.txt wgs32:/var/www/www.ros.org/html/debbuild/
#
# Authors: Tully Foote; Austin Hendrix
#

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
        # TODO: update to self.versions (versions per distro/arch)
        self.version = version


def list_packages(rootdir, update, substring):
    c = apt.Cache(rootdir=rootdir)
    c.open()

    if update:
        c.update()

    c.open() # required to recall open after updating or you will query the old data

    packages = []
    for p in [k for k in c.keys() if args.substring in k]:
#        v = c[p].versions[0]
        packages.append(Package(p, c[p].candidate.version))

    return packages

def render_html(packages, rosdistro):
   # TODO: use the same template engine that apt_root.py uses
   outstr = """<html>
<head>
<title>%s debbuild report</title>
<style type="text/css">
body {
  font-family: Helvetica, Arial, Verdana, sans-serif;
  font-size: 12px;
}
.title {
  background-color: lightgrey;
  padding: 10px;
}
table {
  border: 1px solid lightgrey;
}
th {
  border: 1px solid lightgrey;
}
td {
  font-size: 12px;
  border: 1px solid lightgrey;
}
</style>
</head>
<body>
<h1><span class="title">%s debbuild report</span></h1>
<h2>Repository Status</h2>
"""%(rosdistro, rosdistro)

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

def render_vertical_repo(repo):
   outstr = ""
   packages = sorted(repo.get_packages())

   if len(packages) == 0:
      print "no packages found matching substring"
      return ""

   width = max([len(p) for p in packages])
   pstr = "package"
   outstr += pstr + " "*(width-len(pstr))+ ": " + repo.get_rosdistro() + "|"

   for d,a in repo.iter_distro_arches():
      outstr += "%s_%s|"%(d, a)
   outstr += '\n'

   releases = repo.get_released_versions()
   rosdistro_len = len(repo.get_rosdistro()) + 1

   for p in packages:
      l = len(p)
      outstr += p + " "*(width-l) + ":"
      release_ver = releases[p]
      outstr += release_ver[:rosdistro_len]+' '*max(0, rosdistro_len -len(release_ver) )+('|' if len(release_ver) < rosdistro_len else '>')
      versions = repo.get_package_versions(p)
      print p, versions
      for da in sorted(versions.keys()):
         version = versions[da]
         outstr += version[:len(da)]+' '*max(0, len(da) -len(version) )+('|' if len(version) < len(da) else '>')

      outstr += '\n'

   return outstr

# represent the status of the repository for this ros distro
class Repository:
   def __init__(self, rootdir, rosdistro, distros, arches, url = None, repos = None, update = False):
      if url:
         repos = {'ros': url}
      if not repos:
         raise Exception("No repository arguments")

      self._rosdistro = rosdistro
      self._distros = sorted(distros)
      self._arches = sorted(arches)
      self._rootdir = rootdir
      self._repos = repos
      self._packages = {}

      # TODO: deal with arch for source debs
      # TODO: deal with architecture-independent debs?

      for distro, arch in self.iter_distro_arches():
         dist_arch = "%s_%s"%(distro, arch)
         da_rootdir = os.path.join(self._rootdir, dist_arch)
         buildfarm.apt_root.setup_apt_rootdir(da_rootdir, distro, arch, additional_repos = repos)
         self._packages[dist_arch] = list_packages(da_rootdir, update=update, substring=args.substring)

      # get released version of each stack

      # Wet stack versions from rosdistro
      rd = buildfarm.rosdistro.Rosdistro(rosdistro)
      distro_packages = rd.get_package_list()
      wet_stacks = [Package(buildfarm.rosdistro.debianize_package_name(rosdistro, p), rd.get_version(p)) for p in distro_packages]

      # Dry stack versions from rospkg
      dry_distro = rospkg.distro.load_distro(rospkg.distro.distro_uri(rosdistro))
      dry_stacks = [Package(buildfarm.rosdistro.debianize_package_name(rosdistro, sn), dry_distro.released_stacks[sn].version) for sn in dry_distro.released_stacks]

      # Build a meta-distro+arch for the released version
      self._packages[' '+ rosdistro] = wet_stacks + dry_stacks

   def get_rosdistro(self):
      return self._rosdistro

   # Get the names of all packages
   def get_packages(self):
      return [p.name for p in self._packages[' ' + self._rosdistro]]

   # Get the names and released versions of all packages
   def get_released_versions(self):
      versions = {}
      for p in self._packages[' ' + self._rosdistro]:
         versions[p.name] = p.version
      return versions

   # Get the names of all distros
   def get_distros(self):
      return self._distros

   # Get the names of all arches
   def get_arches(self):
      return self._arches

   # iterate over (distro, arch) tuples
   def iter_distro_arches(self):
      for d in self.get_distros():
         for a in self.get_arches():
            yield (d, a)

   # Get the names and versions of all packages in a specific arch/distro combo
   def get_distro_arch_versions(self, distro, arch):
      return []

   # Get the versions of a package in all distros and arches
   def get_package_versions(self, package_name, distro = None, arch = None):
      versions = {}
      for d, a in self.iter_distro_arches():
         da = "%s_%s"%(d, a)
         versions[da] = ""
         # TODO: refactor our data structure so that this isn't horribly inefficient
         for p in self._packages[da]:
            if p.name == package_name:
               versions[da] = p.version
      return versions

   # Get the version of a package in a specific distro/arch combination
   def get_package_version(self, package_name, distro, arch):
      return self.get_package_versions(package_name, distro, arch)


if __name__ == "__main__":
    args = parse_options()


    if args.rootdir:
        # TODO: resolve rootdir to an absolute path
        rootdir = args.rootdir
    else:  
        rootdir = tempfile.mkdtemp()
        

    arches = ['i386', 'amd64']
    #arches = ['i386', 'amd64', 'source']
    distros = buildfarm.rosdistro.get_target_distros(args.rosdistro)


    ros_repos = buildfarm.apt_root.parse_repo_args(args.repo_urls)

    packages = {}

    try:
        repository = Repository(rootdir, args.rosdistro, distros, arches, repos = ros_repos, update = args.update)
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

    # get released version of each stack

    # Wet stack versions from rosdistro
    rd = buildfarm.rosdistro.Rosdistro(args.rosdistro)
    distro_packages = rd.get_package_list()
    wet_stacks = [Package(buildfarm.rosdistro.debianize_package_name(args.rosdistro, p), rd.get_version(p)) for p in distro_packages]

    # Dry stack versions from rospkg
    dry_distro = rospkg.distro.load_distro(rospkg.distro.distro_uri(args.rosdistro))
    dry_stacks = [Package(buildfarm.rosdistro.debianize_package_name(args.rosdistro, sn), dry_distro.released_stacks[sn].version) for sn in dry_distro.released_stacks]

    # Build a meta-distro+arch for the released version
    packages[' '+ args.rosdistro] = wet_stacks + dry_stacks


#    outstr = render_vertical(packages)
    outstr = render_vertical_repo(repository)
#    outstr = render_html(packages, args.rosdistro)
#    print outstr


    if args.outfile:
        with open(args.outfile, 'w') as of:
            of.write(outstr + '\n')
            print "Wrote output to file %s" % args.outfile
