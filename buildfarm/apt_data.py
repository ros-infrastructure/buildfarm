#!/usr/bin/env python

from __future__ import print_function

import gzip
import logging
import os
import socket
from StringIO import StringIO
import time
import urllib2
import yaml

from rospkg.distro import distro_uri


def get_version_data(rootdir, rosdistro_name, ros_repos, distro_arches, apt_update=True):
    rosdistro_data = RosdistroData(rosdistro_name)

    apt_data = AptData(rosdistro_name)

    # repo type (building, shadow-fixed, ros)
    for repo_type in ros_repos:
        for d in set([d for (d, a) in distro_arches]):
            # download list of source packages
            da_str = "%s_source" % d
            dst_filename = 'Sources'
            url = os.path.join(ros_repos[repo_type], 'dists/%s/main/source/Sources.gz' % d)
            datafile = fetch_gzip_file(rootdir, repo_type, da_str, url, dst_filename, reuse_existing=not apt_update)
            # extract information
            apt_data.fill_versions(repo_type, d, 'source', datafile)

        for (d, a) in distro_arches:
            # download list of binary packages
            da_str = "%s_%s" % (d, a)
            dst_filename = 'Packages'
            url = os.path.join(ros_repos[repo_type], 'dists/%s/main/binary-%s/Packages.gz' % (d, a))
            datafile = fetch_gzip_file(rootdir, repo_type, da_str, url, dst_filename, reuse_existing=not apt_update)
            # extract information
            apt_data.fill_versions(repo_type, d, a, datafile)

    return rosdistro_data, apt_data


class RosdistroData(object):

    def __init__(self, rosdistro_name):
        self.packages = {}
        from buildfarm.ros_distro import Rosdistro
        # for fuerte we still fetch the new groovy rosdistro to get a list of distros
        rd = Rosdistro(rosdistro_name if rosdistro_name != 'fuerte' else 'groovy')
        self.rosdistro_index = rd._index
        self.rosdistro_dist = rd._dist

        # load wet rosdistro packages
        if rosdistro_name == 'fuerte':
            from buildfarm.ros_distro_fuerte import Rosdistro as RosdistroFuerte
            rd = RosdistroFuerte(rosdistro_name)

        for pkg_name in rd.get_package_list():
            version = rd.get_version(pkg_name, full_version=True)
            if version:
                self.packages[pkg_name] = RosdistroVersion(pkg_name, 'wet', version)

        # load dry rosdistro stacks
        if rosdistro_name == 'groovy':
            dry_yaml = yaml.load(urllib2.urlopen(distro_uri(rosdistro_name)))
            stacks = dry_yaml['stacks'] or {}
            for stack_name, d in stacks.items():
                if stack_name == '_rules':
                    continue
                version = d.get('version')
                if version:
                    if stack_name in self.packages:
                        logging.warn("Stack '%s' exists in dry (%s) as well as in wet (%s) distro. Ignoring dry package." % (stack_name, version, self.packages[stack_name].version))
                        continue
                    self.packages[stack_name] = RosdistroVersion(stack_name, 'dry', version)

            # load variants
            variants = dry_yaml['variants'] or {}
            for variant in variants:
                if len(variant) != 1:
                    logging.warn("Not length 1 dict in variant '%s': skipping" % variant)
                    continue
                variant_name = variant.keys()[0]
                if variant_name in self.packages:
                    logging.warn("Variant '%s' exists also as a package in %s. Ignoring variant." % (variant_name, self.packages[variant_name].type))
                    continue
                self.packages[variant_name] = RosdistroVersion(variant_name, 'variant', '1.0.0')


class RosdistroVersion(object):

    def __init__(self, pkg_name, type_, version):
        self.name = pkg_name
        self.type = type_
        self.version = version


class AptData(object):
    def __init__(self, rosdistro_name):
        self.rosdistro_name = rosdistro_name
        self.debian_packages = {}
        self._primary_arch = None  # fill with the first used arch

    def get_version(self, debian_name, repo_type, distro_arch):
        if not debian_name in self.debian_packages:
            return None
        return self.debian_packages[debian_name].get_version(repo_type, distro_arch)

    def fill_versions(self, repo_type, distro, arch, datafile):
        """
        Extract information from apt 'Packages' / 'Sources' list files
        and fill in the versions.
        """
        if not self._primary_arch:
            self._primary_arch = arch

        logging.debug('Reading file: %s' % datafile)
        data = {}
        # split package blocks
        with open(datafile, 'r') as f:
            blocks = f.read().split('\n\n')
        blocks = [b.splitlines() for b in blocks if b]
        # create dict by package name
        for block in blocks:
            prefix = 'Package: '
            assert block[0].startswith(prefix)
            data[block[0][len(prefix):]] = block

        for debian_name in data:
            pkg_data = data[debian_name]
            # extract version of package
            prefix = 'Version: '
            versions = [l for l in pkg_data if l.startswith(prefix)]
            version = versions[0] if len(versions) == 1 else None
            if debian_name not in self.debian_packages:
                self.debian_packages[debian_name] = AptVersion(debian_name)
            self.debian_packages[debian_name].add_version(repo_type, '%s_%s' % (distro, arch), version)


class AptVersion(object):

    def __init__(self, debian_name):
        self.debian_name = debian_name
        self._versions = {}

    def add_version(self, repo_type, distro_arch, version):
        self._versions[(repo_type, distro_arch)] = version

    def get_version(self, repo_type, distro_arch):
        return self._versions.get((repo_type, distro_arch), None)


def load_url(url, retry=2, retry_period=1, timeout=10):
    try:
        fh = urllib2.urlopen(url, timeout=timeout)
    except urllib2.HTTPError as e:
        if e.code == 503 and retry:
            time.sleep(retry_period)
            return load_url(url, retry=retry - 1, retry_period=retry_period, timeout=timeout)
        e.msg += ' (%s)' % url
        raise
    except urllib2.URLError as e:
        if isinstance(e.reason, socket.timeout) and retry:
            time.sleep(retry_period)
            return load_url(url, retry=retry - 1, retry_period=retry_period, timeout=timeout)
        raise urllib2.URLError(str(e) + ' (%s)' % url)
    return fh.read()


def fetch_gzip_file(rootdir, repo_type, da_str, url, dst_filename, reuse_existing=False):
    path = os.path.join(rootdir, repo_type, da_str)
    if not os.path.exists(path):
        os.makedirs(path)
    path = os.path.join(path, dst_filename)
    if not reuse_existing or not os.path.exists(path):
        logging.debug('Downloading apt list file: %s' % url)
        yaml_gz_str = load_url(url)
        yaml_gz_stream = StringIO(yaml_gz_str)
        g = gzip.GzipFile(fileobj=yaml_gz_stream, mode='rb')
        with open(path, 'w') as f:
            f.write(g.read())
    else:
        logging.debug('Reuse apt list file: %s' % path)
    return path
