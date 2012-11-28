#!/usr/bin/env python

import os
import logging
import urllib2
import yaml

import apt
import numpy as np

import buildfarm.apt_root
import buildfarm.rosdistro
from rospkg.distro import distro_uri

ros_repos = {'ros': 'http://packages.ros.org/ros/ubuntu/',
             'shadow-fixed': 'http://packages.ros.org/ros-shadow-fixed/ubuntu/',
             'building': 'http://50.28.27.175/repos/building'}

def make_status_page(repo_da_caches, da_strs, ros_pkgs_table):
    '''
    Returns the contents of an HTML page showing the current
    build status for all wet and dry packages on all
    supported distributions and architectures.

    :param repo_da_caches: from get_repo_da_caches()
    :param da_strs: list of str from get_da_strs()
    :param ros_pkgs_table: numpy array from get_ros_pkgs_table()
    '''
    # Get the version of each Debian package in each ROS apt repository.
    repo_name_da_to_pkgs = dict(((repo_name, da_str), get_pkgs_from_apt_cache(cache))
                                for repo_name, da_str, cache in repo_da_caches)

    # Make in-memory table showing the latest deb version for each package.
    t = make_versions_table(ros_pkgs_table, repo_name_da_to_pkgs, da_strs,
                            ros_repos.keys())

    # Generate HTML from the in-memory table
    return make_csv_from_table(t)

def make_csv_from_table(t):
    '''
    Makes a CSV-formatted string from the contents of numpy table t,
    assumed to have named columns.
    
    >>> t = np.array([(1,2), (3,4)], dtype=[('c1', 'int32'), ('c2', 'int32')])
    >>> make_csv_from_table(t)
    'c1,c2\\n1,2\\n3,4'
    '''
    header = ','.join(t.dtype.names) 
    lines = [','.join(map(str, row)) for row in t]
    return '\n'.join([header] + lines)

def get_repo_da_caches(rootdir, ros_repo_names, da_strs):
    '''
    Returns [(repo_name, da_str, cache_dir), ...]

    For example, get_repo_da_caches('/tmp/ros_apt_caches', ['ros', 'shadow-fixed'], ['quantal_i386'])
    '''
    return [(ros_repo_name, da_str, get_repo_cache_dir_name(rootdir, ros_repo_name, da_str))
            for ros_repo_name in ros_repo_names
            for da_str in da_strs]

def get_apt_cache(dirname):
    c = apt.Cache(rootdir=dirname)
    c.open()
    return c

def get_ros_repo_names(ros_repos):
    return ros_repos.keys()

def get_da_strs(distro_arches):
    return [get_dist_arch_str(d, a) for d, a in distro_arches]

bin_arches = ['amd64', 'i386']

def get_distro_arches(arches):
    distros = buildfarm.rosdistro.get_target_distros('groovy')
    return [(d, a) for d in distros for a in arches]

def make_versions_table(ros_pkgs_table, repo_name_da_to_pkgs, da_strs, repo_names):
    '''
    Returns an in-memory table with all the information that will be displayed:
    ros package names and versions followed by debian versions for each
    distro/arch.
    '''
    left_columns = [('name', object), ('version', object), ('wet', bool),
                    ('ros_apt_repo', object)]
    right_columns = [(da_str, object) for da_str in da_strs]
    columns = left_columns + right_columns
    table = np.empty(len(ros_pkgs_table)*len(repo_names), dtype=columns)

    for i, (name, version, wet) in enumerate(ros_pkgs_table):
        for j, repo_name in enumerate(repo_names):
            for da_str in da_strs:
                index = i * len(repo_names) + j
                table['name'][index] = name
                table['version'][index] = version
                table['wet'][index] = wet
                table['ros_apt_repo'][index] = repo_name
                table[da_str][index] = get_pkg_version(da_str, repo_name_da_to_pkgs, repo_name, name)

    return table

def get_pkg_version(da_str, repo_name_da_to_pkgs, repo_name, name):
    deb_name = buildfarm.rosdistro.debianize_package_name('groovy', name)
    if da_str.endswith('source'):
        # Get the source version from the corresponding amd64 package.
        amd64_da_str = da_str.replace('source', 'amd64')
        p = get_matching_pkg(repo_name_da_to_pkgs, deb_name, repo_name, amd64_da_str)
        return getattr(getattr(p, 'candidate', None), 'source_version', None)
    else:
        p = get_matching_pkg(repo_name_da_to_pkgs, deb_name, repo_name, da_str)
        return getattr(getattr(p, 'candidate', None), 'version', None)

def get_matching_pkg(repo_name_da_to_pkgs, deb_name, repo_name, da_str):
    pkgs = repo_name_da_to_pkgs.get((repo_name, da_str), [])
    matching_pkgs = [p for p in pkgs if p.name == deb_name]
    if not matching_pkgs:
        logging.debug('No package found with name %s on %s repo, %s',
                      deb_name, repo_name, da_str)
        return None
    elif len(matching_pkgs) > 1:
        logging.warn('More than one package found with name %s on %s repo, %s',
                     deb_name, repo_name, da_str)
        return None
    else:
        return matching_pkgs[0]

def get_ros_pkgs_table(wet_names_versions, dry_names_versions):
    return np.array(
        [(name, version, True) for name, version in wet_names_versions] + 
        [(name, version, False) for name, version in dry_names_versions],
        dtype=[('name', object), ('version', object), ('wet', bool)])

def get_dist_arch_str(d, a):
    return "%s_%s" % (d, a)

def get_repo_cache_dir_name(rootdir, ros_repo_name, dist_arch):
    return os.path.join(rootdir, ros_repo_name, dist_arch)

def build_repo_caches(rootdir, ros_repos, distro_arches):
    '''
    Builds (or rebuilds) local caches for ROS apt repos.

    For example, build_repo_caches('/tmp/ros_apt_caches', ros_repos,
                                   get_distro_arches())
    '''
    for repo_name, url in ros_repos.items():
        for distro, arch in distro_arches:
            dist_arch = get_dist_arch_str(distro, arch)
            dir = get_repo_cache_dir_name(rootdir, repo_name, dist_arch)
            build_repo_cache(dir, repo_name, url, distro, arch)

def build_repo_cache(dir, ros_repo_name, ros_repo_url, distro, arch):
    logging.info('Setting up an apt directory at %s', dir)
    repo_dict = {ros_repo_name: ros_repo_url}
    buildfarm.apt_root.setup_apt_rootdir(dir, distro, arch,
                                         additional_repos=repo_dict)
    logging.info('Getting a list of packages for %s-%s', distro, arch)
    cache = apt.Cache(rootdir=dir)
    cache.open()
    cache.update()
    # Have to open the cache again after updating.
    cache.open()

def get_wet_names_versions():
    return get_names_versions(get_wet_names_packages())

def get_dry_names_versions():
    return get_names_versions(get_dry_names_packages())

def get_names_versions(names_pkgs):
    return sorted([(name, d.get('version')) for name, d in names_pkgs],
                  key=lambda (name, version): name)

def get_wet_names_packages():
    '''
    Fetches a yaml file from the web and returns a list of pairs of the form

    [(short_pkg_name, pkg_dict), ...]

    for the wet (catkinized) packages.
    '''
    wet_yaml = get_wet_yaml()
    return wet_yaml['repositories'].items()

def get_wet_yaml():
    url = 'https://raw.github.com/ros/rosdistro/master/releases/groovy.yaml'
    return yaml.load(urllib2.urlopen(url))

def get_dry_names_packages():
    '''
    Fetches a yaml file from the web and returns a list of pairs of the form

    [(short_pkg_name, pkg_dict), ...]

    for the dry (rosbuild) packages.
    '''
    dry_yaml = get_dry_yaml()
    return [(name, d) for name, d in dry_yaml['stacks'].items() if name != '_rules']

def get_dry_yaml():
    return yaml.load(urllib2.urlopen(distro_uri('groovy')))

def get_pkgs_from_apt_cache(cache_dir):
    cache = apt.Cache(rootdir=cache_dir)
    cache.open()
    return [cache[name] for name in cache.keys() if 'ros-groovy' in name]

def render_csv(rootdir):
    arches = bin_arches + ['source']
    da_strs = get_da_strs(get_distro_arches(arches))
    ros_repo_names = get_ros_repo_names(ros_repos)
    repo_da_caches = get_repo_da_caches(rootdir, ros_repo_names, da_strs)
    wet_names_versions = get_wet_names_versions()
    dry_names_versions = get_dry_names_versions()
    ros_pkgs_table = get_ros_pkgs_table(wet_names_versions, dry_names_versions)
    page = make_status_page(repo_da_caches, da_strs, ros_pkgs_table)
    print page

def main():
    import argparse

    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

    # Parse command line args
    p = argparse.ArgumentParser(description='Output deb build status HTML page on stdout')
    rd_help = '''\
Root directory containing ROS apt caches.
This should be created using the build_caches command.
'''
    p.add_argument('command', help='Command: either build_caches or render_csv')
    p.add_argument('rootdir', help=rd_help)
    args = p.parse_args()

    if args.command == 'build_caches':
        build_repo_caches(args.rootdir, ros_repos, get_distro_arches(bin_arches))

    elif args.command == 'render_csv':
        render_csv(args.rootdir)

    else:
        print ('Command %s not recognized. Please specify build_caches or render_csv.' % args.command)

if __name__ == '__main__':
    main()

