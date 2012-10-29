#!/usr/bin/env python

from __future__ import print_function
import argparse
import shutil
import sys
import tempfile
import urllib2
import yaml
import time


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



def trigger_if_not_building(jobname, instance):
    try:
        job_info = instance.get_job_info(jobname)
        #import pprint
        #pp = pprint.PrettyPrinter()
        #pp.pprint(job_info)
        

        if 'inQueue' in job_info:
            if job_info['inQueue']:

                print ("Skipping trigger of job %s because it's already queued" % jobname)
                return True
        if not 'color' in job_info:
            raise Exception("'building' not in job_info as expected")
        if not 'anime' in job_info['color']:
            print ("Triggering %s" % (job_name) )
            jenkins_instance.build_job(job_name)
        else:
            print ("Skipping trigger of job %s because it's already running" % jobname)
        return True
    except Exception, ex:
        print ("Failed to trigger %s: %s" % (job_name, ex))
        return False


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


        for s in sorted(missing.iterkeys()):
            dist_archs = missing[s]
            detected_source = False
            for da in dist_archs:
                if 'source' in da:
                    print("Source missing for %s" % da)
                    detected_source = True

            if detected_source:
                job_name = '%s_sourcedeb' % (debianize_package_name(args.rosdistro, s) )
                trigger_if_not_building(job_name, jenkins_instance)
                print ("Skipping debbuilds for this package [%s] as the sourcedeb will trigger them automatically" % s)
                continue
    
            for da in dist_archs:
                job_name = '%s_binarydeb_%s' % (debianize_package_name(args.rosdistro, s), da )
                trigger_if_not_building(job_name, jenkins_instance)
            time.sleep(1) # jenkins slowdown loop

    else:
        
        print('This was not pushed to the server.  If you want to do so use "--commit" to do it for real.')



    

