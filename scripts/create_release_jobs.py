#!/usr/bin/env python

from __future__ import print_function
import argparse
import os
import shutil
import tempfile

from buildfarm import dependency_walker, jenkins_support, release_jobs

import rospkg.distro

from buildfarm.rosdistro import Rosdistro, debianize_package_name

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
           help='Really?', action='store_true', default=False)
    parser.add_argument('--delete', dest='delete',
           help='Delete extra jobs', action='store_true', default=False)
    parser.add_argument('--no-update', dest='skip_update',
           help='Assume packages have already been downloaded', action='store_true', default=False)
    parser.add_argument('--wet-only', dest='wet_only',
           help='Only setup wet jobs', action='store_true', default=False)
    parser.add_argument('--repo-workspace', action='store',
           help='A directory into which all the repositories will be checked out into.')
    parser.add_argument('--repos', nargs='+',
           help='A list of repository (or stack) names to create. Default: creates all')
    args = parser.parse_args()
    if args.repos and args.delete:
        parser.error('A set of repos to create can not be combined with the --delete option.')
    return args


def doit(distros, fqdn, jobs_graph, rosdistro, commit=False, delete_extra_jobs=False, whitelist_repos=None):
    jenkins_instance = None
    if args.commit or delete_extra_jobs:
        jenkins_instance = jenkins_support.JenkinsConfig_to_handle(jenkins_support.load_server_config_file(jenkins_support.get_default_catkin_debs_config()))

    rd = Rosdistro(rosdistro)

    # Figure out default distros.  Command-line arg takes precedence; if
    # it's not specified, then read targets.yaml.
    if distros:
        default_distros = distros
    else:
        default_distros = rd.get_target_distros()

    # We take the intersection of repo-specific targets with default
    # targets.
    results = {}

    for repo_name in sorted(rd.get_repo_list()):
        if whitelist_repos and repo_name not in whitelist_repos:
            continue

        r = rd.get_repo(repo_name)
        #todo add support for specific targets, needed in rosdistro.py too
        #if 'target' not in r or r['target'] == 'all':
        target_distros = default_distros
        #else:
        #    target_distros = list(set(r['target']) & set(default_distros))

        print ('Configuring WET repo "%s" at "%s" for "%s"' % (r.name, r.url, target_distros))

        for p in sorted(r.packages.iterkeys()):
            if not r.version:
                print('- skipping "%s" since version is null' % r.name)
                continue
            pkg_name = rd.debianize_package_name(p)
            results[pkg_name] = release_jobs.doit(r.url,
                 pkg_name,
                 target_distros,
                 fqdn,
                 jobs_graph,
                 rosdistro=rosdistro,
                 short_package_name=p,
                 commit=commit,
                 jenkins_instance=jenkins_instance)
            #time.sleep(1)
            #print ('individual results', results[pkg_name])

    if args.wet_only:
        print ("wet only selected, skipping dry and delete")
        return results

    if rosdistro == 'backports':
        print ("No dry backports support")
        return results

    #dry stacks
    # dry dependencies
    d = rospkg.distro.load_distro(rospkg.distro.distro_uri(rosdistro))

    for s in sorted(d.stacks.iterkeys()):
        if whitelist_repos and s not in whitelist_repos:
            continue
        print ("Configuring DRY job [%s]" % s)
        if not d.stacks[s].version:
            print('- skipping "%s" since version is null' % s)
            continue
        results[rd.debianize_package_name(s)] = release_jobs.dry_doit(s, default_distros, rosdistro, jobgraph=jobs_graph, commit=commit, jenkins_instance=jenkins_instance)
        #time.sleep(1)

    # special metapackages job
    if not whitelist_repos or 'metapackages' in whitelist_repos:
        results[rd.debianize_package_name('metapackages')] = release_jobs.dry_doit('metapackages', default_distros, rosdistro, jobgraph=jobs_graph, commit=commit, jenkins_instance=jenkins_instance)

    if delete_extra_jobs:
        assert(not whitelist_repos)
        # clean up extra jobs
        configured_jobs = set()

        for jobs in results.values():
            release_jobs.summarize_results(*jobs)
            for e in jobs:
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

    print('Loading rosdistro %s' % args.rosdistro)

    rd = Rosdistro(args.rosdistro)

    workspace = args.repo_workspace
    try:
        if not args.repo_workspace:
            workspace = os.path.join(tempfile.gettempdir(), 'repo-workspace-%s' % args.rosdistro)
        package_co_info = rd.get_package_checkout_info()

        dependencies = dependency_walker.get_jenkins_dependencies(workspace, rd, skip_update=args.skip_update)

        dry_jobgraph = release_jobs.dry_generate_jobgraph(args.rosdistro, dependencies)

        combined_jobgraph = {}
        for k, v in dependencies.iteritems():
            combined_jobgraph[k] = v
        for k, v in dry_jobgraph.iteritems():
            combined_jobgraph[k] = v

        # setup a job triggered by all other debjobs
        combined_jobgraph[debianize_package_name(args.rosdistro, 'metapackages')] = combined_jobgraph.keys()

    finally:
        if not args.repo_workspace:
            shutil.rmtree(workspace)

    results_map = doit(
        args.distros,
        args.fqdn,
        combined_jobgraph,
        rosdistro=args.rosdistro,
        commit=args.commit,
        delete_extra_jobs=args.delete,
        whitelist_repos=args.repos)

    if not args.commit:
        print('This was not pushed to the server.  If you want to do so use "--commit" to do it for real.')
