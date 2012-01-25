#!/usr/bin/env python

from __future__ import print_function
import os
import sys
import argparse
import yaml
import urllib2
import build_job_graph_from_dscs
import create_debjobs
import dependency_walker
import tempfile
import shutil

#import pprint # for debugging only, remove 

URL_PROTOTYPE="https://raw.github.com/willowgarage/rosdistro/master/%s.yaml"

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
           default=['lucid', 'oneiric'])
    parser.add_argument('--commit', dest='commit',
           help='Really?', action='store_true')
    parser.add_argument('--dscs', dest='dscs', action='store', 
           help='A directory with all the dscs that jenkins builds.  If unspecified the dscs will be pulled from the repo into a tempdir.')
    parser.add_argument('--repo-worksapce', dest='repos', action='store', 
           help='A directory into which all the repositories will be checked out into.')
    parser.add_argument('--username',dest='username')
    parser.add_argument('--password',dest='password')
    args = parser.parse_args()
    if args.commit and ( not args.username or not args.password ):
        print('If you are going to commit, you need a username and pass.',file=sys.stderr)
        sys.exit(1)
    return parser.parse_args()

def doit(repo_map, rosdistro, distros, fqdn, jobs_graph, commit = False, username = None, password=None):

    for r in repo_map:
        #TODO add distros parsing 
        #distros = r['target']
        #if r['target'] == 'all':
        #    distros = 
        print (r)
        
        create_debjobs.doit(r['url'], rosdistro, distros, fqdn, jobs_graph, commit, username, password)

    return

if __name__ == "__main__":
    args = parse_options()
    repo = "http://"+args.fqdn+"/repos/building"
    job_graph = build_job_graph_from_dscs.build_graph(repo, args.dscs)

    repo_map = yaml.load(urllib2.urlopen(URL_PROTOTYPE%args.rosdistro))
    print (repo_map)
    
    workspace = args.repos
    try:
        if not args.repos:
            workspace = tempfile.mkdtemp()
            
        dependencies = dependency_walker.get_dependencies(workspace, repo_map)

    finally:
        if not args.repos:
            shutil.rmtree(workspace)

    #print ("RESULT DEPENDENCIES", dependencies)
    #print ("job_graph", job_graph)

    #pp = pprint.PrettyPrinter(indent=4)
    #pp.pprint(dependencies)
    #pp.pprint(job_graph)

    doit(repo_map, args.rosdistro, args.distros, args.fqdn, dependencies, args.commit, args.username, args.password)
