#!/bin/env python

from rosdistro import sanitize_package_name, debianize_package_name
from stack_of_remote_repository import get_packages_of_remote_repository

import os.path
import copy
import shutil

from vcstools.vcs_abstraction import VcsClient
from vcstools.git import GitClient
from vcstools.vcs_base import VcsError
import catkin_pkg.package as catpak
from catkin_pkg.package import InvalidPackage

def simplify_repo_name(repo_url):
    """Return a path valid version of the repo_url"""
    return os.path.basename(repo_url)

class VcsFileCache(object):
    """A class to support caching gbp repos for querying specific files from a repo"""

    def __init__(self, cache_location):
        # make sure the cache dir exists and ifnot create it
        if not os.path.exists(cache_location):
            os.makedirs(cache_location)
        self._cache_location = cache_location

    def _get_file(self, repo_type, repo_url, version, filename):
        """ Fetch the file specificed by filename relative to the root of the repository"""
        name = simplify_repo_name(repo_url)
        repo_path = os.path.join(self._cache_location, name)
        #client = VcsClient(repo_type, repo_path)
        client = GitClient(repo_path) # using git only
        if client.path_exists():
            updated = True
            if client.get_url() == repo_url:
                updated = client.update(version)
            if not updated:
                print("WARNING: Repo at %s changed url from %s to %s.  Redownloading!" % (repo_path, client.get_url(), repo_url) )
                shutil.rmtree(repo_path)
                client.checkout(repo_url, version, shallow=True)
                # git only
                client._do_fetch()
        else:
            client.checkout(repo_url, version, shallow=True)

        full_filename = os.path.join(repo_path, filename)
        if not os.path.exists(full_filename):
            raise VcsError("Requested file %s missing from repo %s version %s (viewed at version %s).  It was expected at: %s" % 
                            ( filename, repo_url, version, client.get_version(), full_filename ) )


        return full_filename

    def get_file_contents(self, repo_type, repo_url, version, filename):
        f = self._get_file(repo_type, repo_url, version, filename)
        with open(f, 'r') as fh:
            contents = fh.read()
            return contents

def prune_self_depends(packages, package):
    if package.name in [p.name for p in packages]:
        print("ERROR: Recursive dependency of %s on itself, pruning this dependency" % (package.name) )
        for p in packages:
            if p.name == package.name:
                packages.remove(p)
                break


def _print_package_set(packages):
    print (", ".join([p.name for p in packages]) )

def _get_depends(packages, package, recursive=False, buildtime=False):
    if buildtime:
        immediate_depends = set([packages[d.name] for d in package.build_depends if d.name in packages] + [packages[d.name] for d in package.buildtool_depends if d.name in packages])
    else:
        immediate_depends = set([packages[d.name] for d in package.run_depends if d.name in packages])
    prune_self_depends(immediate_depends, package)

    result = copy.copy(immediate_depends)

    if recursive:
        for d in immediate_depends:
            if d.name in packages:
                result |= _get_depends(packages, d, recursive, buildtime)
                prune_self_depends(result, package)
            else:
                print("skipping missing dependency %s. not in %s" % (d.name, packages.keys()))
    
                
    return result
    

def get_jenkins_dependencies(workspace, rd_obj, skip_update=False):
    packages = {}

    vcs_cache = VcsFileCache(workspace)

    checkout_info = rd_obj.get_package_checkout_info()
    for pkg_name in sorted(checkout_info.keys()):
        pkg_info = checkout_info[pkg_name]
        try:
            pkg_string = vcs_cache.get_file_contents('git', 
                                                     pkg_info['url'],
                                                     pkg_info['version'],
                                                     'package.xml')#os.path.join(pkg_info['relative_path'], 'package.xml') )
            try:
                p = catpak.parse_package_string(pkg_string)
                packages[p.name] = p
            except InvalidPackage as ex:
                print('package.xml for %s is invalid.  Error: %s' % (pkg_name, ex))
        except VcsError as ex:
            print("Failed to get package.xml for %s.  Error: %s" %
                  (pkg_name, ex) )
                  



    result = {}
    for pkg_name in sorted(packages.keys()):
        p = packages[pkg_name]
        deb_name = debianize_package_name(rd_obj._rosdistro, 
                                          p.name)
        build_depends = _get_depends(packages, p, recursive=False, buildtime=True)
        run_depends = _get_depends(packages, p, recursive=False, buildtime=False)
        

        
        # switching to only set first level dependencies to clean up clutter in jenkins instead of the recursive ones below
        result[deb_name] = [debianize_package_name(rd_obj._rosdistro, d.name) for d in build_depends | run_depends ]
        continue

        runtime_of_build = set()
        for d in build_depends:
            runtime_of_build |= _get_depends(packages, p, recursive=True, buildtime = False)
        #result[deb_name] = build_depends | run_depends | runtime_of_build
        result[deb_name] = [debianize_package_name(rd_obj._rosdistro, d.name) for d in build_depends | run_depends | runtime_of_build ]


    return result
