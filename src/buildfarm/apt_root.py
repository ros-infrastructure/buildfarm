#!/usr/bin/env python

from __future__ import print_function
import em
import os
import pprint

class Templates(object):
    template_dir = os.path.dirname(__file__)
    sources = os.path.join(template_dir, 'sources.list.em') #basic sources
    ros_sources = os.path.join(template_dir, 'ros-sources.list.em') #ros sources
    apt_conf = os.path.join(template_dir, 'apt.conf.em') #apt.conf
    arch_conf = os.path.join(template_dir, 'arch.conf.em') #arch.conf

def expand_file(config_template, d):
    with open(config_template) as fh:
        file_em = fh.read()
    s = em.expand(file_em, **d)
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
        except OSError, ex:
            if ex.errno == 17:
                continue
            raise ex

def setup_conf(rootdir, target_dir):
    """ Set the apt.conf config settings for the specific
    architecture. """

    d = {'rootdir':rootdir}
    with open(os.path.join(target_dir, "apt.conf"), 'w') as apt_conf:
        apt_conf.write(expand_file(Templates.apt_conf, d))


    
def set_default_sources(rootdir, distro, repo):
    """ Set the source lists for the default ubuntu and ros sources """
    d = {'distro':distro, 
         'repo': repo}
    with open(os.path.join(rootdir, "etc/apt/sources.list"), 'w') as sources_list:
        sources_list.write(expand_file(Templates.sources, d))

def set_additional_sources(rootdir, distro, repo, source_name):
    """ Set the source lists for the default ubuntu and ros sources """
    d = {'distro':distro, 
         'repo': repo}
    with open(os.path.join(rootdir, "etc/apt/sources.list.d/%s.list"%source_name), 'w') as sources_list:
        sources_list.write(expand_file(Templates.ros_sources, d))
    

def setup_apt_rootdir(rootdir, distro, arch, mirror=None, additional_repos = {}):
    setup_directories(rootdir)
    if not mirror:
        repo='http://us.archive.ubuntu.com/ubuntu/'
    else:
        repo = mirror
    set_default_sources(rootdir, distro, repo)
    for repo_name, repo_url in additional_repos.iteritems():
        set_additional_sources(rootdir, distro, repo_url, repo_name)

    d = {'arch':arch}
    path = os.path.join(rootdir, "etc/apt/apt.conf.d/51Architecture")
    with open(path, 'w') as arch_conf:
        arch_conf.write(expand_file(Templates.arch_conf, d))


def parse_repo_args(repo_args):
    """ Split the repo argument listed as "repo_name@repo_url" into a map"""
    ros_repos = {}
    
    for a in repo_args:
        n, u = a.split('@')
        ros_repos[n] = u

    return ros_repos

