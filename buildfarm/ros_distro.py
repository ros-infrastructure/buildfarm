#!/usr/bin/env python


from __future__ import print_function

import sys
import urllib2
import yaml

from rosdistro import get_cached_release, get_index, get_index_url, get_release_build_files, get_release_file

class RepoMetadata(object):
    def __init__(self, name, url, version, packages = {}, status = None):
        self.name = name
        self.url = url
        self.full_version = version
        if version:
            self.version = version.split('-')[0]
        else:
            self.version = None
        self.status = status
        self.packages = packages


def sanitize_package_name(name):
    return name.replace('_', '-')


def debianize_package_name(rosdistro, name):
    if rosdistro == 'backports':
        return sanitize_package_name(name)
    return sanitize_package_name("ros-%s-%s"%(rosdistro, name))


def undebianize_package_name(rosdistro, name):
    if rosdistro != 'backports':
        prefix = 'ros-%s-' % rosdistro
        assert(name.startswith(prefix))
        name = name[len(prefix):]
    return name.replace('-', '_')


# todo raise not exit
class Rosdistro:
    def __init__(self, rosdistro_name):
        self._rosdistro = rosdistro_name
        self._targets = None
        self._index = get_index(get_index_url())
        if self._rosdistro not in self._index.distributions:
            print ("Unknown distribution '%s'" % self._rosdistro, file=sys.stderr)
            sys.exit(1)
        self._dist = get_cached_release(self._index, self._rosdistro)
        self._build_files = get_release_build_files(self._index, self._rosdistro)

        self._repoinfo = {}
        self._package_in_repo = {}
        for name, repo in self._dist.repositories.iteritems():
            self._repoinfo[name] = RepoMetadata(name, repo.url, repo.version)
            self._repoinfo[name].packages = {}
            for pkg_name in repo.package_names:
                pkg = self._dist.packages[pkg_name]
                self._repoinfo[name].packages[pkg_name] = pkg.subfolder
                self._package_in_repo[pkg_name] = name

    def get_arches(self):
        arches = []
        for arches_per_distro in self._build_files[0].targets.values():
            for arch in arches_per_distro:
                if arch not in arches:
                    arches.append(arch)
        return arches

    def get_package_xml(self, pkg_name):
        return self._dist.get_package_xml(pkg_name)

    def debianize_package_name(self, package_name):
        return debianize_package_name(self._rosdistro, package_name)

    def get_repo_list(self):
        return self._repoinfo.iterkeys()

    def get_repos(self):
        return self._repoinfo.itervalues()

    def get_repo(self, name):
        return self._repoinfo[name]

    def get_package_list(self):
        packages = set()
        for repo, repo_obj in self._repoinfo.iteritems():
            packages |= set(repo_obj.packages.keys())
        return packages

    def get_package_checkout_info(self):
        packages = {}
        for repo, info  in self._repoinfo.iteritems():
            for p, path in info.packages.iteritems():
                if info.version == None: 
                    print ("Skipping repo %s due to null version" % p)
                    continue
                packages[p] = {'url': info.url, 
                               'version': 'release/%s/%s' % (p, info.version), 
                               'full_version': 'release/%s/%s/%s' % (self._rosdistro, p, info.full_version), 
                               'relative_path': path}
        return packages

    def get_version(self, package_name, full_version = False):
        if package_name in self._package_in_repo:
            if full_version:
                return self._repoinfo[self._package_in_repo[package_name]].full_version
            else:
                return self._repoinfo[self._package_in_repo[package_name]].version
        else:
            return None

    def get_status(self, stack_name):
        if stack_name in self._repoinfo.keys():
            return self._repoinfo[stack_name].status
        else:
            return None

    def get_target_distros(self):
        if self._targets is None: # Different than empty list
            self._targets = get_target_distros(self._rosdistro)
        return self._targets

    def get_default_target(self):
        if self._targets is None:
            self.get_target_distros()
        if len(self._targets) == 0:
            print("Warning no targets defined for distro %s"%self._rosdistro)
            return None
        return self._targets[0]

    def get_stack_rosinstall_snippet(self, distro = None):
        if not distro:
            distro = self.get_default_target()
        raise NotImplemented
            

    def compute_rosinstall_snippet(self, local_name, gbp_url, version, distro_name):

        if version is None:
            print ("Error version unset for %s"%local_name)
            return None
        config = {}
        config['local-name'] = local_name

        config['version'] = 'upstream/%s'%version
        config['version'] = 'debian/ros-%s-%s_%s_%s'%(self._rosdistro, local_name, version, distro_name)
        #config['version'] = '%s-%s'%(local_name, version)
        config['uri'] = gbp_url
        return {'git': config}


    def compute_rosinstall_distro(self, rosdistro, distro_name):
        rosinstall_data = [self.compute_rosinstall_snippet(name, r['url'], r['version'], rosdistro) for name, r in self.repo_map['repositories'].items() if 'url' in r and 'version' in r]
        return rosinstall_data
        


def get_target_distros(rosdistro):
    print("Fetching targets")
    index = get_index(get_index_url())
    rel_file = get_release_file(index, rosdistro)
    return rel_file.platforms
