#!/usr/bin/env python

from __future__ import print_function

from pkg_resources import resource_string
import em
import errno
import os
import urllib
import urlparse


def expand_template(config_template, d):
    s = em.expand(config_template, **d)
    return s


def setup_directories(rootdir):
    """ Create the directories needed to use apt with an alternate
    rootdir """

    # create the directories needed
    dirs = ["etc/apt/sources.list.d",
            "etc/apt/apt.conf.d",
            "etc/apt/preferences.d",
            "var/lib/apt/lists/partial",
            "var/cache/apt/archives/partial",
            "var/lib/dpkg"
            ]

    for d in dirs:
        try:
            os.makedirs(os.path.join(rootdir, d))
        except OSError as ex:
            if ex.errno == 17:
                continue
            raise ex

    # create empty files needed
    files = ["var/lib/dpkg/status"]
    for f in files:
        fullname = os.path.join(rootdir, f)
        if not os.path.exists(fullname):
            open(fullname, 'w').close()


def setup_conf(rootdir, target_dir, arch):
    """ Set the apt.conf config settings for the specific
    architecture. """

    d = {'rootdir': rootdir,
         'arch': arch}
    with open(os.path.join(target_dir, "apt.conf"), 'w') as apt_conf:
        template = resource_string('buildfarm',
                                   'resources/templates/apt.conf.em')
        apt_conf.write(expand_template(template, d))


def set_default_sources(rootdir, distro, repo):
    """ Set the source lists for the default ubuntu and ros sources """
    d = {'distro': distro,
         'repo': repo}
    with open(os.path.join(rootdir, "etc/apt/sources.list"),
              'w') as sources_list:
        template = resource_string('buildfarm',
                                   'resources/templates/sources.list.em')
        sources_list.write(expand_template(template, d))


def set_additional_sources(rootdir, distro, repo, source_name):
    """ Set the source lists for the default ubuntu and ros sources """
    d = {'distro': distro,
         'repo': repo}
    with open(os.path.join(rootdir,
                           "etc/apt/sources.list.d/%s.list" % source_name),
              'w') as sources_list:
        template = resource_string('buildfarm',
                                   'resources/templates/ros-sources.list.em')
        sources_list.write(expand_template(template, d))


def setup_apt_rootdir(rootdir,
                      distro, arch,
                      mirror=None,
                      additional_repos={},
                      gpg_key_urls=[]):
    setup_directories(rootdir)
    if not mirror:
        if arch in ['amd64', 'i386']:
            if distro in ['oneiric', 'quantal', 'raring', 'saucy']:
                repo = 'http://old-releases.ubuntu.com/ubuntu/'
            else:
                repo = 'http://us.archive.ubuntu.com/ubuntu/'
        else:
            repo = 'http://ports.ubuntu.com/ubuntu-ports/'
    else:
        repo = mirror
    set_default_sources(rootdir, distro, repo)
    for repo_name, repo_url in additional_repos.iteritems():
        set_additional_sources(rootdir, distro, repo_url, repo_name)

    d = {'arch': arch}
    path = os.path.join(rootdir, "etc/apt/apt.conf.d/51Architecture")
    with open(path, 'w') as arch_conf:
        template = resource_string('buildfarm',
                                   'resources/templates/arch.conf.em')
        arch_conf.write(expand_template(template, d))

    key_dir = os.path.join(rootdir,
                           'etc', 'apt', 'trusted.gpg.d')

    # make sure the directory is there
    if gpg_key_urls:
        try:
            os.makedirs(key_dir)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(key_dir):
                pass
            else:
                raise

    for gpg_key_url in gpg_key_urls:
        elements = urlparse.urlparse(gpg_key_url)
        base = os.path.basename(elements[2])
        filename = os.path.join(key_dir, base + '.gpg')
        urllib.urlretrieve(gpg_key_url,
                           filename)


def parse_repo_args(repo_args):
    """ Split the repo argument listed as "repo_name@repo_url" into a map"""
    ros_repos = {}

    for a in repo_args:
        n, u = a.split('@')
        ros_repos[n] = u

    return ros_repos
