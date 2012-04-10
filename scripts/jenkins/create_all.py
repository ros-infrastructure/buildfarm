#!/usr/bin/env python

from __future__ import print_function
import os
import sys
import argparse
import yaml
import urllib2
import create_debjobs
import dependency_walker
import tempfile
import shutil

#import pprint # for debugging only, remove 

URL_PROTOTYPE="https://raw.github.com/ros/rosdistro/master/releases/%s.yaml"

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
    parser.add_argument('--repo-workspace', dest='repos', action='store', 
           help='A directory into which all the repositories will be checked out into.')
    parser.add_argument('--username',dest='username')
    parser.add_argument('--password',dest='password')
    args = parser.parse_args()
    if args.commit and ( not args.username or not args.password ):
        print('If you are going to commit, you need a username and pass.',file=sys.stderr)
        sys.exit(1)
    return parser.parse_args()

def doit(repo_map, package_names_by_url, distros, fqdn, jobs_graph, commit = False, username = None, password=None):

    # What ROS distro are we configuring?
    rosdistro = repo_map['release-name']
        
    # Figure out default distros.  Command-line arg takes precedence; if
    # it's not specified, then read targets.yaml.
    if distros:
        default_distros = distros
    else:
        print("Fetching " + URL_PROTOTYPE%'targets')
        targets_map = yaml.load(urllib2.urlopen(URL_PROTOTYPE%'targets'))
        my_targets = [x for x in targets_map if rosdistro in x]
        if len(my_targets) != 1:
            print("Must have exactly one entry for rosdistro %s in targets.yaml"%(rosdistro))
            sys.exit(1)
        default_distros = my_targets[0][rosdistro]

    # We take the intersection of repo-specific targets with default
    # targets.
    results = {}
    for r in repo_map['gbp-repos']:
        if 'url' not in r or 'name' not in r:
            print("'name' and/or 'url' keys missing for repository %s; skipping"%(r))
            continue
        url = r['url']
        if url not in package_names_by_url:
            print("Repo %s is missing from the list; must have been skipped (e.g., for missing a stack.yaml)"%(r))
            continue
        if 'target' in r:
            if r['target'] == 'all':
                target_distros = default_distros
            else:
                target_distros = list(set(r['target']) & default_distros)
        else:
            target_distros = default_distros

        print ("Configuring %s for %s"%(r['url'], target_distros))
        
        results[package_names_by_url[url]] = create_debjobs.doit(url, package_names_by_url[url], target_distros, fqdn, jobs_graph, commit, username, password)
        print ("individual results", results[package_names_by_url[url]])

    return results

if __name__ == "__main__":
    args = parse_options()
    repo = "http://"+args.fqdn+"/repos/building"

    print("Fetching " + URL_PROTOTYPE%args.rosdistro)
    repo_map = yaml.load(urllib2.urlopen(URL_PROTOTYPE%args.rosdistro))
    if 'release-name' not in repo_map:
        print("No 'release-name' key in yaml file")
        sys.exit(1)
    if repo_map['release-name'] != args.rosdistro:
        print('release-name mismatch (%s != %s)'%(repo_map['release-name'],args.rosdistro))
        sys.exit(1)
    if 'gbp-repos' not in repo_map:
        print("No 'gbp-repos' key in yaml file")
        sys.exit(1)

    workspace = args.repos
    try:
        if not args.repos:
            workspace = tempfile.mkdtemp()
            
        (dependencies, package_names_by_url) = dependency_walker.get_dependencies(workspace, repo_map['gbp-repos'], args.rosdistro)

    finally:
        if not args.repos:
            shutil.rmtree(workspace)

    results_map = doit(repo_map, package_names_by_url, args.distros, args.fqdn, dependencies, args.commit, args.username, args.password)
    for k, v in results_map.iteritems():
        create_debjobs.summarize_results(*v)


    if not args.commit:
        print("This was not pushed to the server.  If you want to do so use ",
              "--commit to do it for real.")
