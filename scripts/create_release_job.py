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

import rospkg.distro


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
           help='The name for the package'),
    parser.add_argument('--dry', dest='dry', help="this is a dry stack", 
                        action='store_true', default=False)
    parser.add_argument('--repo-workspace', dest='repos', action='store',
           help='A directory into which all the repositories will be checked out into.')
    return parser.parse_args()




def get_dependencies(workspace, repositories, rosdistro):

    if not workspace:
        do_delete = True
        ws = tempfile.mkdtemp()
    else:
        do_delete = False
        ws = workspace
    try:
        (dependencies, pkg_by_url) = buildfarm.dependency_walker.get_dependencies(ws, repositories , rosdistro)

    finally:
        if do_delete is True:
            shutil.rmtree(workspace)

    return (dependencies, pkg_by_url)

if __name__ == '__main__':
    args = parse_options()

    jenkins_instance = None
    if args.commit:
        jenkins_instance = jenkins_support.JenkinsConfig_to_handle(jenkins_support.load_server_config_file(jenkins_support.get_default_catkin_debs_config()))


    rd = buildfarm.rosdistro.Rosdistro(args.rosdistro)

    # use default target platforms from wet for both
    if args.distros:
        default_distros = args.distros
    else:
        default_distros = rd.get_target_distros()


    # Create a unified dependency tree in jobgraph
    (dependencies, pkg_by_url) = get_dependencies(args.repos, rd.repo_map['repositories'], args.rosdistro)

    jobgraph = buildfarm.release_jobs.dry_generate_jobgraph(args.rosdistro, dependencies) 

    for k, v in dependencies.iteritems():
        jobgraph[k] = v

    if args.dry:
        print('Configuring "%s" for "%s"' % (args.package_name, default_distros))


        results = buildfarm.release_jobs.dry_doit(args.package_name, default_distros, args.rosdistro, jobgraph, args.commit, jenkins_instance)




    else:

        


        # Figure out default distros.  Command-line arg takes precedence; if
        # it's not specified, then read targets.yaml.




    
        # We take the intersection of repo-specific targets with default
        # targets.
        if args.package_name not in rd.repo_map['repositories']:
            print('No such package %s' % args.package_name)
            sys.exit(1)
        r = rd.repo_map['repositories'][args.package_name]
        if 'url' not in r:
            print('"name" and/or "url" keys missing for repository "%s" for key %s; skipping' % (r, args.package_name) )
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


        results = buildfarm.release_jobs.doit(url, pkg_by_url[url], target_distros, args.fqdn, jobgraph, args.rosdistro, args.package_name, args.commit, jenkins_instance)


    buildfarm.release_jobs.summarize_results(*results)
    if not args.commit:
        print('This was not pushed to the server.  If you want to do so use "--commit" to do it for real.')
