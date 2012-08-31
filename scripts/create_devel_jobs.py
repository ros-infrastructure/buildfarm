#!/usr/bin/env python

from __future__ import print_function
import argparse
import shutil
import sys
import tempfile
import urllib2
import yaml

from buildfarm import devel_jobs, jenkins_support
from buildfarm.stack_of_remote_repository import get_stack_of_remote_repository

#import pprint # for debugging only, remove

URL_PROTOTYPE = 'https://raw.github.com/ros/rosdistro/master/releases/%s.yaml'


def parse_options():
    parser = argparse.ArgumentParser(
             description='Create a set of jenkins jobs '
             'for continuous integration for a catkin package.')
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


def doit(repo_map, stacks, distros, fqdn, rosdistro, commit=False, delete_extra_jobs=False):
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
        if 'type' not in r or 'url' not in r:
            print('"type" or "url" key missing for repository "%s"; skipping' % r)
            continue
        vcs_type = r['type']
        url = r['url']
        version = None
        if vcs_type != 'svn':
            if 'version' not in r:
                print('"version" key missing for SVN repository "%s"; skipping' % r)
                continue
            else:
                version = r['version']
        if 'target' not in r or r['target'] == 'all':
            target_distros = default_distros
        else:
            target_distros = list(set(r['target']) & set(default_distros))

        print ('Configuring "%s" for "%s"' % (r['url'], target_distros))

        results[short_package_name] = devel_jobs.doit(vcs_type, url, version,
             short_package_name,
             stacks[short_package_name],
             target_distros,
             fqdn,
             rosdistro=rosdistro,
             short_package_name=short_package_name,
             commit=commit,
             jenkins_instance=jenkins_instance)
        print ('individual results', results[short_package_name])

    if delete_extra_jobs:
        # clean up extra jobs
        configured_jobs = set()

        for _, v in results.iteritems():
            devel_jobs.summarize_results(*v)
            for e in v:
                configured_jobs.update(set(e))

        existing_jobs = set([j['name'] for j in jenkins_instance.get_jobs()])
        relevant_jobs = existing_jobs - configured_jobs
        relevant_jobs = [j for j in relevant_jobs if j.startswith('ros-%s-' % rosdistro) and '_devel_' in j]

        for j in relevant_jobs:
            print('Job "%s" detected as extra' % j)
            if commit:
                jenkins_instance.delete_job(j)
                print('Deleted job "%s"' % j)

    return results


if __name__ == '__main__':
    args = parse_options()
    repo = 'http://%s/repos/building' % args.fqdn

    print('Fetching "%s"' % (URL_PROTOTYPE % (args.rosdistro + '-devel')))
    repo_map = yaml.load(urllib2.urlopen(URL_PROTOTYPE % (args.rosdistro + '-devel')))
    if 'release-name' not in repo_map:
        print('No "release-name" key in yaml file')
        sys.exit(1)
    if repo_map['release-name'] != args.rosdistro:
        print('release-name mismatch (%s != %s)' % (repo_map['release-name'], args.rosdistro))
        sys.exit(1)
    if 'repositories' not in repo_map:
        print('No "repositories" key in yaml file')
    if 'type' not in repo_map or repo_map['type'] != 'devel':
        print('Wrong type value in yaml file')
        sys.exit(1)

    workspace = args.repos
    try:
        if not args.repos:
            workspace = tempfile.mkdtemp()
        stacks = {}
        for name, repo in repo_map['repositories'].items():
            stacks[name] = get_stack_of_remote_repository(name, repo['type'], repo['url'], repo['version'] if 'version' in repo else None)

    finally:
        if not args.repos:
            shutil.rmtree(workspace)

    results_map = doit(repo_map,
        stacks,
        args.distros,
        args.fqdn,
        rosdistro=args.rosdistro,
        commit=args.commit,
        delete_extra_jobs=args.delete)

    if not args.commit:
        print('This was not pushed to the server.  If you want to do so use "--commit" to do it for real.')
