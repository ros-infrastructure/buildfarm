#!/usr/bin/env python

from __future__ import print_function
import em
import os
import argparse
import pprint

def parse_options():
    parser = argparse.ArgumentParser(
             description='setup a directory to be used as a rootdir for apt')
    parser.add_argument('--fqdn', dest='fqdn',
           help='The source repo to push to, fully qualified something...',
           default='50.28.27.175')
    parser.add_argument(dest='distro',
           help='The debian release distro, lucid, oneiric, etc')
    parser.add_argument(dest='architecture',
           help='The debian binary architecture. amd64, i386, armel')
    parser.add_argument(dest='rootdir',
           help='The rootdir to use')
    return parser.parse_args()

class Templates(object):
    template_dir = os.path.dirname(__file__)
    sources = os.path.join(template_dir, 'sources.list.em') #basic sources
    ros_sources = os.path.join(template_dir, 'ros-sources.list.em') #ros sources
    apt_conf = os.path.join(template_dir, 'apt.conf.em') #apt.conf
    arch_conf = os.path.join(template_dir, 'arch.conf.em') #arch.conf

def expand(config_template, d):
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
            "var/lib/apt/lists/partial"
            ]
    
    for d in dirs:
        try:
            os.makedirs(os.path.join(rootdir, d))
        except OSError, ex:
            if ex.errno == 17:
                continue
            raise ex

def generate_dictonary(server, distro):
    d = {'distro':distro, 'repo_url':"http://%(server)s/repos/building"%locals(),
         'src_repo_url':"http://%(server)s/repos/building"%locals()}
    return d    

def setup_conf(rootdir, arch):
    """ Set the apt.conf config settings for the specific
    architecture. """

    d = {'rootdir':rootdir}
    with open(os.path.join(rootdir, "apt.conf"), 'w') as apt_conf:
        apt_conf.write(expand(Templates.apt_conf, d))

    d = {'arch':arch}
    with open(os.path.join(rootdir, "etc/apt/apt.conf.d/51Architecture"), 'w') as arch_conf:
        arch_conf.write(expand(Templates.arch_conf, d))

    
def set_sources(rootdir, server, distro, arch):
    """ Set the source lists for the default ubuntu and ros sources """
    d = generate_dictonary(server, distro)
    with open(os.path.join(rootdir, "etc/apt/sources.list"), 'w') as sources_list:
        sources_list.write(expand(Templates.sources, d))
    with open(os.path.join(rootdir, "etc/apt/sources.list.d/ros-sources.list"), 'w') as sources_list:
        sources_list.write(expand(Templates.ros_sources, d))
    

def doit():
    args = parse_options()
    print(args)

    setup_directories(args.rootdir)
    setup_conf(args.rootdir, args.architecture)
    set_sources(args.rootdir, args.fqdn, args.distro, args.architecture)


if __name__ == "__main__":
    doit()
