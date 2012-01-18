#!/usr/bin/env python

from __future__ import print_function
import os
import sys
import argparse
import yaml
import urllib2
import build_job_graph_from_dscs
import create_debjobs

URL_PROTOTYPE="https://raw.github.com/willowgarage/3rdparty-debbuilds/master/%s.yaml"

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
    

    doit(repo_map, args.rosdistro, args.distros, args.fqdn, job_graph, args.commit, args.username, args.password)
