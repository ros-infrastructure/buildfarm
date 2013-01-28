#!/usr/bin/env python

from __future__ import print_function

import argparse
import pprint

from buildfarm import jenkins_support, release_jobs
from buildfarm.rosdistro import debianize_package_name


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
    parser.add_argument('--sourcedeb-only', action='store_true', default=False,
           help='Only check sourcedeb jobs. Default: all')
    parser.add_argument('--commit', dest='commit',
           help='Really?', action='store_true')
    return parser.parse_args()


def trigger_if_necessary(da, pkg, rosdistro, jenkins_instance, missing_by_arch):
    if da != 'source' and 'source' in missing_by_arch and pkg in missing_by_arch['source']:
        print ("  Skipping trigger of binarydeb job for package '%s' on arch '%s' as the sourcedeb job will trigger them automatically" % (pkg, da))
        return False

    if da == 'source':
        job_name = '%s_sourcedeb' % (debianize_package_name(rosdistro, pkg))
    else:
        job_name = '%s_binarydeb_%s' % (debianize_package_name(rosdistro, pkg), da)
    job_info = jenkins_instance.get_job_info(job_name)

    if 'color' in job_info and 'anime' in job_info['color']:
        print ("  Skipping trigger of job %s because it's already running" % job_name)
        return False

    if 'inQueue' in job_info and job_info['inQueue']:
        print ("  Skipping trigger of job '%s' because it's already queued" % job_name)
        return False

    if da != 'source' and 'upstreamProjects' in job_info:
        upstream = job_info['upstreamProjects']
        for p in missing_by_arch[da]:
            p_name = '%s_binarydeb_%s' % (debianize_package_name(rosdistro, p), da)
            for u in upstream:
                if u['name'] == p_name:
                    print ("  Skipping trigger of job '%s' because the upstream job '%s' is also triggered" % (job_name, p_name))
                    return False

    print ("Triggering '%s'" % (job_name))
    jenkins_instance.build_job(job_name)
    return True


if __name__ == '__main__':
    args = parse_options()

    missing = release_jobs.compute_missing(
        args.distros,
        args.fqdn,
        rosdistro=args.rosdistro,
        sourcedeb_only=args.sourcedeb_only)

    pp = pprint.PrettyPrinter()
    print ("net Missing")
    pp.pprint(missing)

    if args.commit:
        jenkins_instance = jenkins_support.JenkinsConfig_to_handle(jenkins_support.load_server_config_file(jenkins_support.get_default_catkin_debs_config()))

        missing_by_arch = {}
        for pkg in sorted(missing.iterkeys()):
            dist_archs = missing[pkg]
            for da in dist_archs:
                if da not in missing_by_arch:
                    missing_by_arch[da] = []
                missing_by_arch[da].append(pkg)

        triggered = 0
        skipped = 0
        for da in missing_by_arch:
            for pkg in missing_by_arch[da]:
                try:
                    success = trigger_if_necessary(da, pkg, args.rosdistro, jenkins_instance, missing_by_arch)
                    if success:
                        triggered += 1
                    else:
                        skipped += 1
                except Exception as ex:
                    print("Failed to trigger package '%s' on arch '%s': %s" % (pkg, da, ex))

        print('Triggered %d jobs, skipped %d jobs.' % (triggered, skipped))

    else:
        print('This was not pushed to the server.  If you want to do so use "--commit" to do it for real.')
