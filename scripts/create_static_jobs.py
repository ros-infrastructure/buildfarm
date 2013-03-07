#!/usr/bin/env python

from __future__ import print_function

import argparse
import difflib
import jenkins
import os
import sys
from xml.etree import ElementTree

from buildfarm import jenkins_support


def parse_arguments(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Create/update a set of Jenkins jobs.')
    parser.add_argument(dest='jobs', nargs='*', metavar='JOBNAME', help='The job to create/update')
    parser.add_argument('--commit', action='store_true', default=False, help='Really?')
    return parser.parse_args(args)


def compare_configs(a, b):
    a_root = ElementTree.fromstring(a)
    b_root = ElementTree.fromstring(b)
    a_str = ElementTree.tostring(a_root)
    b_str = ElementTree.tostring(b_root)
    return a_str == b_str, a_str, b_str


def create_jenkins_job(jenkins_instance, name, config, commit):
    try:
        jobs = jenkins_instance.get_jobs()
        if name in [job['name'] for job in jobs]:
            remote_config = jenkins_instance.get_job_config(name)
            configs_equal, remote_config_cleaned, config_cleaned = compare_configs(remote_config, config)
            if not configs_equal:
                print("Reconfiguring job '%s'" % name)
                if commit:
                    jenkins_instance.reconfig_job(name, config)
                else:
                    print('  not performed.')
                diff = difflib.unified_diff(remote_config_cleaned.splitlines(), config_cleaned.splitlines(), 'remote', name + '.xml', n=0, lineterm='')
                for line in diff:
                    print(line)
                print('')
            else:
                print("Skipping job '%s' as config is the same" % name)
        else:
            print("Creating job '%s'" % name)
            if commit:
                jenkins_instance.create_job(name, config)
            else:
                print('  not performed.')
        return True
    except jenkins.JenkinsException as e:
        print("Failed to configure job '%s': %s" % (name, e), file=sys.stderr)
        return False


if __name__ == '__main__':
    args = parse_arguments()

    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'static_jobs')

    templates = []
    for entry in sorted(os.listdir(template_dir)):
        if not entry.endswith('.xml'):
            continue
        templates.append(entry[:-4])

    jobs = []
    if args.jobs:
        for job in args.jobs:
            if job not in templates:
                print("Unknown job '%s'" % job, file=sys.stderr)
            else:
                jobs.append(job)
    else:
        for template in templates:
            jobs.append(template)

    jenkins_instance = jenkins_support.JenkinsConfig_to_handle(jenkins_support.load_server_config_file(jenkins_support.get_default_catkin_debs_config()))

    for job in jobs:
        template_filename = os.path.join(template_dir, job + '.xml')
        with open(template_filename, 'r') as f:
            config = f.read()
            create_jenkins_job(jenkins_instance, job, config, args.commit)
