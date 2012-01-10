#!/usr/bin/env python

from __future__ import print_function
import em
import os
import argparse
import pprint

def parse_options():
    parser = argparse.ArgumentParser(
             description='setup a directory to be used as a rootdir for apt')
    parser.add_argument('--repo', dest='repo_urls', action='append',metavar=['REPO_NAME@REPO_URL'],
           help='The name for the source and the url such as ros@http://50.28.27.175/repos/building')
    parser.add_argument(dest='distro',
           help='The debian release distro, lucid, oneiric, etc')
    parser.add_argument(dest='architecture',
           help='The debian binary architecture. amd64, i386, armel')
    parser.add_argument(dest='rootdir',
           help='The rootdir to use')
    parser.add_argument('--local-conf-dir',dest='local_conf',
                      help='A directory to write an apt-conf to use with apt-get update.')
    args = parser.parse_args()
    

    if not args.repo_urls:
        #default to devel machine for now
        args.repo_urls = ['ros@http://50.28.27.175/repos/building']
        
    for a in args.repo_urls:
        if not '@' in a:
            parser.error("Invalid repo definition: %s"%a)
    

    return args

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

def setup_conf(rootdir, arch, target_dir):
    """ Set the apt.conf config settings for the specific
    architecture. """

    d = {'rootdir':rootdir}
    with open(os.path.join(target_dir, "apt.conf"), 'w') as apt_conf:
        apt_conf.write(expand_file(Templates.apt_conf, d))

    d = {'arch':arch}
    with open(os.path.join(rootdir, "etc/apt/apt.conf.d/51Architecture"), 'w') as arch_conf:
        arch_conf.write(expand_file(Templates.arch_conf, d))

    
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

def parse_repo_args(repo_args):
    """ Split the repo argument listed as "repo_name@repo_url" into a map"""
    ros_repos = {}
    
    for a in repo_args:
        n, u = a.split('@')
        ros_repos[n] = u

    return ros_repos

def doit():
    args = parse_options()
    #print(args)
    #print( [a.split('@') for a in args.repo_urls] )
    
            

    ros_repos = parse_repo_args(args.repo_urls)

    setup_apt_rootdir(args.rootdir, args.distro, args.architecture, additional_repos = ros_repos) 
    if args.local_conf:
        setup_conf(rootdir, arch, args.local_conf)


if __name__ == "__main__":
    doit()
