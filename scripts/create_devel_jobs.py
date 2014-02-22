#!/usr/bin/env python

from __future__ import print_function

import argparse
import difflib
import jenkins
import os
import pkg_resources
import sys
from xml.etree import ElementTree

from buildfarm import jenkins_support
import rosdistro

def parse_arguments(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Create/update a set of Jenkins jobs.')
    parser.add_argument(dest='jobs', nargs='*', metavar='package', help='The job to create/update')
    parser.add_argument('--rosdistro', dest='rosdistro', help='The rosdistro')
    parser.add_argument('--commit', action='store_true', default=False, help='Really?')
    return parser.parse_args(args)



def compute_job_name(repo_name, rosdistro):
    return 'docker-devel-%s-%s' % (rosdistro, repo_name)



if __name__ == '__main__':
    args = parse_arguments()
        

    config_template = pkg_resources.resource_string('buildfarm', 'resources/templates/devel_jobs/devel_config.xml.em') 

    
    ind = rosdistro.get_index(rosdistro.get_index_url())

    df = rosdistro.get_distribution_file(ind, args.rosdistro)
    
    source_jobs = {}

    for r, v in df.repositories.items():
        data = v.get_data()
        if 'source' not in data:
            continue

        source_jobs[r] = data['source']
            


    print("source jobs", source_jobs)


    jobs = []


    jenkins_instance = jenkins_support.JenkinsConfig_to_handle(jenkins_support.load_server_config_file(jenkins_support.get_default_catkin_debs_config()))

    for repo_name, params in source_jobs.items():
        if args.jobs and repo_name not in args.jobs:
            print("Skipping %s since not passed as a parameter" % repo_name)
            continue
        job_name = compute_job_name(repo_name, args.rosdistro)
        params['job_name'] = job_name
        #print(params)
        config = jenkins_support.expand(config_template, params)
        #print(config)
        
        jenkins_support.create_jenkins_job(jenkins_instance, job_name, config, args.commit)


