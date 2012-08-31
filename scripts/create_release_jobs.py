#!/usr/bin/env python

from __future__ import print_function
import argparse
import shutil
import sys
import tempfile
import urllib2
import yaml

from buildfarm import dependency_walker, jenkins_support, release_jobs

import rospkg.distro

from buildfarm.rosdistro import debianize_package_name

#import pprint # for debugging only, remove

URL_PROTOTYPE = 'https://raw.github.com/ros/rosdistro/master/releases/%s.yaml'


def parse_options():
    parser = argparse.ArgumentParser(
             description='Create a set of jenkins jobs '
             'for source debs and binary debs for a catkin package.')
    parser.add_argument('--fqdn', dest='fqdn',
           help='The source repo to push to, fully qualified something...',
           default='50.28.27.175')
    parser.add_argument(dest='rosdistro',
           help='The ros distro. electric, fuerte, groovy')
    parser.add_argument('--distros', nargs='+',
           help='A list of debian distros. Default: %(default)s',
           default=[])
    parser.add_argument('--commit', dest='commit',
           help='Really?', action='store_true')
    parser.add_argument('--delete', dest='delete',
           help='Delete extra jobs', action='store_true')
    parser.add_argument('--repo-workspace', dest='repos', action='store',
           help='A directory into which all the repositories will be checked out into.')
    return parser.parse_args()


def doit(repo_map, package_names_by_url, distros, fqdn, jobs_graph, rosdistro, commit=False, delete_extra_jobs=False):
    jenkins_instance = None
    if args.commit or delete_extra_jobs:
        jenkins_instance = jenkins_support.JenkinsConfig_to_handle(jenkins_support.load_server_config_file(jenkins_support.get_default_catkin_debs_config()))

    # What ROS distro are we configuring?
    rosdistro = repo_map['release-name']
    
    

    # Figure out default distros.  Command-line arg takes precedence; if
    # it's not specified, then read targets.yaml.
    if distros:
        default_distros = distros
    else:
        print('Fetching "%s"' % (URL_PROTOTYPE % 'targets'))
        targets_map = yaml.load(urllib2.urlopen(URL_PROTOTYPE % 'targets'))
        my_targets = [x for x in targets_map if rosdistro in x]
        if len(my_targets) != 1:
            print('Must have exactly one entry for rosdistro "%s" in targets.yaml' % rosdistro)
            sys.exit(1)
        default_distros = my_targets[0][rosdistro]

    # We take the intersection of repo-specific targets with default
    # targets.
    results = {}
    for short_package_name, r in repo_map['repositories'].items():
        if 'url' not in r:
            print('"url" key missing for repository "%s"; skipping' % r)
            continue
        url = r['url']
        if url not in package_names_by_url:
            print('Repo "%s" is missing from the list; must have been skipped (e.g., for missing a stack.xml)' % r)
            continue
        if 'target' not in r or r['target'] == 'all':
            target_distros = default_distros
        else:
            target_distros = list(set(r['target']) & set(default_distros))

        print ('Configuring WET stack "%s" for "%s"' % (r['url'], target_distros))

        results[package_names_by_url[url]] = release_jobs.doit(url,
             package_names_by_url[url],
             target_distros,
             fqdn,
             jobs_graph,
             rosdistro=rosdistro,
             short_package_name=short_package_name,
             commit=commit,
             jenkins_instance=jenkins_instance)
        print ('individual results', results[package_names_by_url[url]])


        

    #dry stacks
    # dry dependencies
    d = rospkg.distro.load_distro(rospkg.distro.distro_uri(rosdistro))

    for s in d.stacks:
        print ("Configuring DRY job [%s]" % s)
        results[debianize_package_name(rosdistro, s) ] = release_jobs.dry_doit(s, default_distros, rosdistro, jobgraph=jobs_graph, commit=commit, jenkins_instance=jenkins_instance)

    if delete_extra_jobs:
        # clean up extra jobs
        configured_jobs = set()

        for _, v in results.iteritems():
            release_jobs.summarize_results(*v)
            for e in v:
                configured_jobs.update(set(e))

        existing_jobs = set([j['name'] for j in jenkins_instance.get_jobs()])
        relevant_jobs = existing_jobs - configured_jobs
        relevant_jobs = [j for j in relevant_jobs if rosdistro in j and ('sourcedeb' in j or 'binarydeb' in j)]

        for j in relevant_jobs:
            print('Job "%s" detected as extra' % j)
            if commit:
                jenkins_instance.delete_job(j)
                print('Deleted job "%s"' % j)

    return results


if __name__ == '__main__':
    args = parse_options()
    repo = 'http://%s/repos/building' % args.fqdn

    print('Fetching "%s"' % (URL_PROTOTYPE % args.rosdistro))
    repo_map = yaml.load(urllib2.urlopen(URL_PROTOTYPE % args.rosdistro))
    if 'release-name' not in repo_map:
        print('No "release-name" key in yaml file')
        sys.exit(1)
    if repo_map['release-name'] != args.rosdistro:
        print('release-name mismatch (%s != %s)' % (repo_map['release-name'], args.rosdistro))
        sys.exit(1)
    if 'repositories' not in repo_map:
        print('No "repositories" key in yaml file')
    if 'type' not in repo_map or repo_map['type'] != 'gbp':
        print('Wrong type value in yaml file')
        sys.exit(1)

    workspace = args.repos
    try:
        if not args.repos:
            workspace = tempfile.mkdtemp()
        (dependencies, package_names_by_url) = dependency_walker.get_dependencies(workspace, repo_map['repositories'], args.rosdistro)
        dry_jobgraph = release_jobs.dry_generate_jobgraph(args.rosdistro) 
        
        combined_jobgraph = {}
        for k, v in dependencies.iteritems():
            combined_jobgraph[k] = v
        for k, v in dry_jobgraph.iteritems():
            combined_jobgraph[k] = v

    finally:
        if not args.repos:
            shutil.rmtree(workspace)

    results_map = doit(repo_map,
        package_names_by_url,
        args.distros,
        args.fqdn,
        combined_jobgraph,
        rosdistro=args.rosdistro,
        commit=args.commit,
        delete_extra_jobs=args.delete)


    if not args.commit:
        print('This was not pushed to the server.  If you want to do so use "--commit" to do it for real.')
