#!/usr/bin/env python

from __future__ import print_function
import argparse
import shutil
import sys
import tempfile

import buildfarm.dependency_walker
import buildfarm.jenkins_support as jenkins_support
import buildfarm.release_jobs
import buildfarm.rosdistro


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


if __name__ == '__main__':
    args = parse_options()

    rd = buildfarm.rosdistro.Rosdistro(args.rosdistro)

    # backwards compatibility
    repo_map = rd.repo_map

    workspace = args.repos
    try:
        if not args.repos:
            workspace = tempfile.mkdtemp()
        (dependencies, pkg_by_url) = buildfarm.dependency_walker.get_dependencies(workspace, repo_map['repositories'], args.rosdistro)

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
    if args.package_name not in repo_map['repositories']:
        print('No such package %s' % args.package_name)
        sys.exit(1)
    r = repo_map['repositories'][args.package_name]
    if 'url' not in r or 'name' not in r:
        print('"name" and/or "url" keys missing for repository "%s"; skipping' % r)
        sys.exit(0)
    url = r['url']
    if url not in pkg_by_url:
        print('Repo "%s" is missing from the list; must have been skipped (e.g., for missing a stack.xml)' % r)
        sys.exit(0)
    if 'target' not in r or r['target'] == 'all':
        target_distros = default_distros
    else:
        target_distros = list(set(r['target']) & default_distros)

    print('Configuring "%s" for "%s"' % (r['url'], target_distros))

    jenkins_instance = None
    if args.commit:
        jenkins_instance = jenkins_support.JenkinsConfig_to_handle(jenkins_support.load_server_config_file(jenkins_support.get_default_catkin_debs_config()))

    results = buildfarm.release_jobs.doit(url, pkg_by_url[url], target_distros, args.fqdn, dependencies, args.rosdistro, args.package_name, args.commit, jenkins_instance)
    buildfarm.release_jobs.summarize_results(*results)
    if not args.commit:
        print('This was not pushed to the server.  If you want to do so use "--commit" to do it for real.')
