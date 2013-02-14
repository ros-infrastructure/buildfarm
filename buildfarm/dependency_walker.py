#!/bin/env python

from rosdistro import debianize_package_name

import os.path
import copy
import shutil
import time
import logging
import sys

from vcstools.git import GitClient
from vcstools.vcs_base import VcsError
from catkin_pkg.package import parse_package_string
from catkin_pkg.package import InvalidPackage


def simplify_repo_name(repo_url):
    """Return a path valid version of the repo_url"""
    return os.path.basename(repo_url)



class VcsFileCache(object):
    """A class to support caching gbp repos for querying specific files from a repo"""

    def __init__(self, cache_location, skip_update):
        # make sure the cache dir exists and ifnot create it
        if not os.path.exists(cache_location):
            os.makedirs(cache_location)
        self._cache_location = cache_location
        self._skip_update = skip_update 

        logger = logging.getLogger('vcstools')
        for h in logger.handlers:
            logger.removeHandler(h)
        logger.addHandler(logging.StreamHandler(sys.stdout))

    def _get_file(self, repo_type, repo_url, version, filename):
        """ Fetch the file specificed by filename relative to the root of the repository"""
        name = simplify_repo_name(repo_url)
        repo_path = os.path.join(self._cache_location, name)
        #client = VcsClient(repo_type, repo_path)
        client = GitClient(repo_path)  # using git only
        updated = False
        if client.path_exists():
            if client.get_url() == repo_url:
                if not self._skip_update:
                    updated = client.update(version, force_fetch=True)
                else:
                    updated = client._do_update(version)
            if not updated:
                shutil.rmtree(repo_path)
        if not updated:
            updated = client.checkout(repo_url, version)

        if not updated:
            raise VcsError("Impossible to update/checkout repo '%s' with version '%s'." % (repo_url, version))

        full_filename = os.path.join(repo_path, filename)
        if not os.path.exists(full_filename):
            raise VcsError("Requested file '%s' missing from repo '%s' version '%s' (viewed at version '%s').  It was expected at: %s" %
                           (filename, repo_url, version, client.get_version(), full_filename))

        return full_filename

    def get_file_contents(self, repo_type, repo_url, version, filename):
        f = self._get_file(repo_type, repo_url, version, filename)
        with open(f, 'r') as fh:
            contents = fh.read()
            return contents


def prune_self_depends(packages, package):
    if package.name in [p.name for p in packages]:
        print("ERROR: Recursive dependency of %s on itself, pruning this dependency" % (package.name))
        for p in packages:
            if p.name == package.name:
                packages.remove(p)
                break


def _print_package_set(packages):
    print (", ".join([p.name for p in packages]))


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


def get_packages(workspace, rd_obj, skip_update=False):
    packages = {}

    vcs_cache = VcsFileCache(workspace, skip_update=skip_update)

    errors = []
    urls_updated = set([])
    checkout_info = rd_obj.get_package_checkout_info()
    for pkg_name in sorted(checkout_info.keys()):
        pkg_info = checkout_info[pkg_name]
        url = pkg_info['url']
        print("Get '%s' from '%s' from tag '%s'" % (pkg_name, url, pkg_info['version']))
        url_updated_before = url in urls_updated
        urls_updated.add(url)
        vcs_cache._skip_update = skip_update or url_updated_before
        try:
            pkg_string = vcs_cache.get_file_contents('git',
                                                     url,
                                                     pkg_info['version'],
                                                     'package.xml')  # os.path.join(pkg_info['relative_path'], 'package.xml'))
            try:
                p = parse_package_string(pkg_string)
                packages[p.name] = p
            except InvalidPackage as ex:
                print("package.xml for '%s' is invalid.  Error: %s" % (pkg_name, ex))
                errors.append(pkg_name)
        except VcsError as ex:
            print("Failed to get package.xml for '%s'.  Error: %s" % (pkg_name, ex))
            errors.append(pkg_name)

        if not vcs_cache._skip_update:
            print("Sleeping for github slowdown")
            time.sleep(1)

    if errors:
        raise RuntimeError('Could not fetch stacks: %s' % ', '.join(errors))

    return packages


def get_jenkins_dependencies(rosdistro, packages):
    result = {}
    for pkg_name in sorted(packages.keys()):
        p = packages[pkg_name]
        deb_name = debianize_package_name(rosdistro, p.name)
        build_depends = _get_depends(packages, p, recursive=False, buildtime=True)
        run_depends = _get_depends(packages, p, recursive=False, buildtime=False)

        # switching to only set first level dependencies to clean up clutter in jenkins instead of the recursive ones below
        result[deb_name] = [debianize_package_name(rosdistro, d.name) for d in build_depends | run_depends]
        continue

    return result
