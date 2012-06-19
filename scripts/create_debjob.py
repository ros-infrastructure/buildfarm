#!/usr/bin/env python

from __future__ import print_function
import em
import os
import sys
from xml.sax.saxutils import escape
import argparse

import yaml
import tempfile
import shutil
import urllib2

import buildfarm.rosdistro

import jenkins

import buildfarm.dependency_walker
import buildfarm.debjobs
import buildfarm.jenkins_support as jenkins_support


def parse_options():
    parser = argparse.ArgumentParser(
             description='Create a set of jenkins jobs '
             'for source debs and binary debs for a catkin package.')
    parser.add_argument('--fqdn', dest='fqdn',
           help='The source repo to push to, fully qualified something...',
           default='50.28.27.175')
    parser.add_argument(dest='rosdistro',
           help='The ros distro. electric, fuerte, galapagos')
    parser.add_argument('--distros', nargs='+',
           help='A list of debian distros. Default: %(default)s',
           default=[])
    parser.add_argument('--commit', dest='commit',
           help='Really?', action='store_true')
    parser.add_argument(dest='package_name',
           help='The name for the package')
    parser.add_argument('--repo-workspace', dest='repos', action='store', 
           help='A directory into which all the repositories will be checked out into.')
    return parser.parse_args()



if __name__ == "__main__":
    args = parse_options()

    rd = buildfarm.rosdistro.Rosdistro(args.rosdistro)

    # backwards compatability
    repo_map = rd.repo_map 

    workspace = args.repos
    try:
        if not args.repos:
            workspace = tempfile.mkdtemp()
            
        (dependencies, pkg_by_url)  = buildfarm.dependency_walker.get_dependencies(workspace, repo_map['gbp-repos'], args.rosdistro)

    finally:
        if not args.repos:
            shutil.rmtree(workspace)

    # Figure out default distros.  Command-line arg takes precedence; if
    # it's not specified, then read targets.yaml.
    if args.distros:
        default_distros = args.distros
    else:
        default_distros = rd.get_target_distros()

    # We take the intersection of repo-specific targets with default
    # targets.
    r = [x for x in repo_map['gbp-repos'] if 'name' in x and x['name'] == args.package_name]
    if len(r) != 1:
        print("No such package %s"%(args.package_name))
        sys.exit(1)
    r = r[0]
    if 'url' not in r or 'name' not in r:
        print("'name' and/or 'url' keys missing for repository %s; skipping"%(r))
        sys.exit(0)
    url = r['url']
    if url not in pkg_by_url:
        print("Repo %s is missing from the list; must have been skipped (e.g., for missing a stack.xml)"%(r))
        sys.exit(0)
    if 'target' in r:
        if r['target'] == 'all':
            target_distros = default_distros
        else:
            target_distros = list(set(r['target']) & default_distros)
    else:
        target_distros = default_distros

    print ("Configuring %s for %s"%(r['url'], target_distros))


    jenkins_instance = None
    if args.commit:
        jenkins_instance = jenkins_support.JenkinsConfig_to_handle(jenkins_support.load_server_config_file(jenkins_support.get_default_catkin_debs_config()))

    results = buildfarm.debjobs.doit(url, pkg_by_url[url], target_distros, args.fqdn, dependencies, args.rosdistro, args.package_name, args.commit, jenkins_instance)
    buildfarm.debjobs.summarize_results(*results)
    if not args.commit:
        print("This was not pushed to the server.  If you want to do so use ",
              "--commit to do it for real.")
