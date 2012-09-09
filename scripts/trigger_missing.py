#!/usr/bin/env python

from __future__ import print_function
import argparse
import shutil
import sys
import tempfile
import urllib2
import yaml



import pprint

from buildfarm import dependency_walker, jenkins_support, release_jobs

import rospkg.distro

from buildfarm.rosdistro import debianize_package_name

import buildfarm.repo




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
    return parser.parse_args()




if __name__ == '__main__':
    args = parse_options()



    missing = release_jobs.compute_missing(
        args.distros,
        args.fqdn,
        rosdistro=args.rosdistro)

    pp = pprint.PrettyPrinter()
    print ("net Missing")
    pp.pprint (missing)


    if args.commit:
        jenkins_instance = jenkins_support.JenkinsConfig_to_handle(jenkins_support.load_server_config_file(jenkins_support.get_default_catkin_debs_config()))


        for s, dist_archs in missing.iteritems():
            if 'source' in dist_archs:
                job_name = '%s_sourcedeb' % (debianize_package_name(args.rosdistro, s) )
                print ("Triggering %s" % (job_name) )
                try:
                    jenkins_instance.build_job(job_name)
                except Exception, ex:
                    print ("Failed to trigger %s: %s" % (job_name, ex))
                # don't trigger binaries as the sourcedeb will trigger them anyway
                continue
    
            for da in dist_archs:
                job_name = '%s_binarydeb_%s' % (debianize_package_name(args.rosdistro, s), da )
                print ("Triggering %s" % (job_name) )
                try: 
                    jenkins_instance.build_job(job_name)
                except Exception, ex:
                    print ("Failed to trigger %s: %s" % (job_name, ex) )


    else:
        
        print('This was not pushed to the server.  If you want to do so use "--commit" to do it for real.')



    

