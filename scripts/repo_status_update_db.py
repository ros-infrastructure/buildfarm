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
#  list_all.py --rosdistro=groovy --substring ros-groovy -u --sqlite3_db=groovy.db --table=building
#  list_all.py --rosdistro=groovy --substring ros-groovy -u --repo shadow@http://packages.ros.org/ros-shadow-fixed/ubuntu/ --sqlite3_db=groovy.db --table=testing
#  list_all.py --rosdistro=groovy --substring ros-groovy -u --repo shadow@http://packages.ros.org/ros/ubuntu/ --sqlite3_db=groovy.db --table=public
#  scp -o StrictHostKeyChecking=no groovy_building.txt groovy_public.txt groovy_testing.txt wgs32:/var/www/www.ros.org/html/debbuild/
#
# Authors: Tully Foote; Austin Hendrix; Issac Trotts
#

import argparse
import logging
import os
import shutil
import sqlite3
import tempfile

import apt

import buildfarm.apt_root #setup_apt_root
import buildfarm.rosdistro

import rospkg.distro

def parse_options():
    desc = "List all packages available in the repos for each arch.  Filter on substring if provided"
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument("--rootdir", dest="rootdir", default = None,
                        help='The directory for apt to use as a rootdir')
    parser.add_argument("--rosdistro", dest='rosdistro', default = None,
                        help='The ros distro. electric, fuerte, groovy')
    parser.add_argument("--substring", dest="substring", default="",
                        help="substring to filter packages displayed default = 'ros-ROSDISTRO'")
    parser.add_argument("-u", "--update", dest="update", action='store_true', default=False,
                        help="Update the cache from the server")
    parser.add_argument('--repo', dest='repo_urls', action='append',metavar=['REPO_NAME@REPO_URL'],
                        help='The name for the source and the url such as ros@http://50.28.27.175/repos/building')
    parser.add_argument('--sqlite3_db', dest='sqlite3_db', default=None,
                        help='Path to SQLite3 db where results will be stored.')
    parser.add_argument('--table', dest='table', default=None,
                        help='Name of table to (re-)create in the SQLite3 db.')
    parser.add_argument('--max-distro-arches', dest='max_distro_arches', type=int,
                        default=0,
                        help='Maximum number of (distro, arch) pairs to process. 0 for unlimited.')

    args = parser.parse_args()

    if not args.rosdistro:
        parser.error('Please specify a distro with --rosdistro=groovy etc.')

    if not args.sqlite3_db:
        parser.error('Please specify --sqlite3_db.')

    if not args.table:
        parser.error('Please specify --table.')

    # default for now to use our devel server
    if not args.repo_urls:
        args.repo_urls =['ros@http://50.28.27.175/repos/building']
    for a in args.repo_urls:
        if not '@' in a:
            parser.error("Invalid repo definition: %s"%a)

    if not args.substring:
        args.substring = 'ros-%s'%args.rosdistro

    infinity = int(1e9)  # close enough
    args.max_distro_arches = args.max_distro_arches or infinity

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
        packages.append(Package(p, c[p].candidate.version))

    return packages


def render_vertical_repo(repo):
    from prettytable import PrettyTable
    header = get_table_header(repo)
    t = PrettyTable(header)
    for row in yield_rows_of_packages_table(repo):
        t.add_row(row)
    return str(t)

def create_table_with_rows(db, table_name, header, rows):
    """
    Creates a table in an SQLite db with the given name, header and rows.
    If the table already exists, it will be overwritten.

    >>> db = sqlite3.connect(':memory:')
    >>> create_table_with_rows(db, 'tbl', header=['a', 'b'], rows=[(1, 2), (2, 3)])
    >>> db.commit()
    >>> c = db.cursor()
    >>> c.execute('select * from tbl').fetchall()
    [(1, 2), (2, 3)]
    """
    columns_str = ', '.join(header)
    db.execute('drop table if exists %s' % table_name)
    db.execute('create table %s(%s)' % (table_name, columns_str))
    slots_str = ', '.join(len(header)*['?'])
    sql = 'insert into %s(%s) values (%s)' % (table_name, columns_str, slots_str)
    db.executemany(sql, rows)

def get_table_header(repo):
    distro_arch_strs = ['%s_%s' % (d, a) for d, a in repo.distro_arches]
    return ["package", repo.get_rosdistro()] + distro_arch_strs

def yield_rows_of_packages_table(repo):
    packages = sorted(repo.get_packages())
    if not packages:
        print "no packages found matching substring"
        return

    releases = repo.get_released_versions()
    for p in packages:
        versions = repo.get_package_versions(p)
        yield tuple([p, releases[p]] + [versions[da] for da in sorted(versions.keys())])

def debname(rosdistro, name):
    return buildfarm.rosdistro.debianize_package_name(rosdistro, name)

# represent the status of the repository for this ros distro
class Repository:
    def __init__(self, rootdir, rosdistro, distro_arches, url = None, repos = None, update = False):
        if url:
            repos = {'ros': url}
        if not repos:
            raise Exception("No repository arguments")

        self.distro_arches = distro_arches
        self._rosdistro = rosdistro
        self._rootdir = rootdir
        self._repos = repos
        self._packages = {}
        self._package_set = None

        # TODO: deal with arch for source debs
        # TODO: deal with architecture-independent debs?

        for distro, arch in distro_arches:
            dist_arch = "%s_%s"%(distro, arch)
            da_rootdir = os.path.join(self._rootdir, dist_arch)
            logging.info('Setting up an apt root directory at %s', da_rootdir)
            buildfarm.apt_root.setup_apt_rootdir(da_rootdir, distro, arch, additional_repos = repos)
            # TODO: collect packages in a better data structure
            logging.info('Getting a list of packages for %s-%s', distro, arch)
            self._packages[dist_arch] = list_packages(da_rootdir, update=update, substring=args.substring)

        # Wet stack versions from rosdistro
        rd = buildfarm.rosdistro.Rosdistro(rosdistro)
        distro_packages = rd.get_package_list()
        wet_stacks = [Package(debname(rosdistro, p), rd.get_version(p)) for p in distro_packages]

        # Dry stack versions from rospkg
        uri = rospkg.distro.distro_uri(rosdistro)
        logging.info('Loading distro at %s', uri)
        dry_distro = rospkg.distro.load_distro(uri)
        stack_names = dry_distro.released_stacks
        dry_stacks = [Package(debname(rosdistro, name), dry_distro.released_stacks[name].version)
                      for name in stack_names]

        # TODO: better data structure
        # Build a meta-distro+arch for the released version
        self._packages[' '+ rosdistro] = wet_stacks + dry_stacks

    def get_rosdistro(self):
        return self._rosdistro

    # Get the names of all packages
    def get_packages(self):
        if not self._package_set:
            # TODO: refactor our data structure so that this is cleaner
            package_set = set()
            for da in self._packages:
                package_set.update([p.name for p in self._packages[da]])
            self._package_set = package_set
        return self._package_set

    # Get the names and released versions of all packages
    def get_released_versions(self):
        versions = {}
        # TODO: refactor our data structure so that we don't have to do this
        for p in self._package_set:
            versions[p] = ""
        for p in self._packages[' ' + self._rosdistro]:
            versions[p.name] = p.version
        return versions

    # iterate over (distro, arch) tuples
    def iter_distro_arches(self):
        return self._distro_arches

    # Get the names and versions of all packages in a specific arch/distro combo
    def get_distro_arch_versions(self, distro, arch):
        return []

    # Get the versions of a package in all distros and arches
    def get_package_versions(self, package_name, distro = None, arch = None):
        # TODO: honor optional arguments
        versions = {}
        for d, a in self.distro_arches:
            da = "%s_%s"%(d, a)
            versions[da] = ""
            # TODO: refactor our data structure so that this isn't horribly inefficient
            for p in self._packages[da]:
                if p.name == package_name:
                    versions[da] = p.version
        return versions

    # Get the version of a package in a specific distro/arch combination
    def get_package_version(self, package_name, distro, arch):
        # TODO
        return self.get_package_versions(package_name, distro, arch)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    args = parse_options()

    db = sqlite3.connect(args.sqlite3_db)

    if args.rootdir:
        # TODO: resolve rootdir to an absolute path
        rootdir = args.rootdir
    else:
        rootdir = tempfile.mkdtemp()

    arches = ['i386', 'amd64', 'source']
    distros = buildfarm.rosdistro.get_target_distros(args.rosdistro)

    ros_repos = buildfarm.apt_root.parse_repo_args(args.repo_urls)

    packages = {}

    try:
        distro_arches = [(d, a) for d in sorted(distros) for a in sorted(arches)]
        distro_arches = distro_arches[:args.max_distro_arches]
        repository = Repository(rootdir, args.rosdistro, distro_arches, repos = ros_repos, update = args.update)
        for d, a in distro_arches:
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
    wet_stacks = [Package(debname(args.rosdistro, p), rd.get_version(p)) for p in distro_packages]

    # Dry stack versions from rospkg
    dry_distro = rospkg.distro.load_distro(rospkg.distro.distro_uri(args.rosdistro))
    dry_stacks = [Package(debname(args.rosdistro, sn), dry_distro.released_stacks[sn].version)
                  for sn in dry_distro.released_stacks]

    # Build a meta-distro+arch for the released version
    packages[' '+ args.rosdistro] = wet_stacks + dry_stacks

    header = get_table_header(repository)
    rows = yield_rows_of_packages_table(repository)
    create_table_with_rows(db, args.table, header, list(rows))
    db.commit()

    logging.info("Wrote output to %s", args.sqlite3_db)
