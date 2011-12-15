#!/usr/bin/env python

from __future__ import print_function
import em
import os
from urllib import urlencode
from xml.sax.saxutils import escape

def parse_options():
    import argparse
    parser = argparse.ArgumentParser(description='Create a jenkins job for building sourcedebs.')
    parser.add_argument(dest='release_uri',
            help='A release repo uri..')
    parser.add_argument('--fqdn', dest='fqdn',
            help='The source repo to push to, fully qualified something or other...', default='50.28.27.175')
    parser.add_argument(dest='rosdistro', help='The ros distro. electric, fuerte, galapagos')
    parser.add_argument('--distros', nargs='+',
            help='A list of debian distros. Default: %(default)s',
            default=['lucid', 'natty', 'oneiric'])
    parser.add_argument('--commit', dest='commit', help='Really?', action='store_true')
    return parser.parse_args()

def expand(config_template, d):
    with open(config_template) as fh:
        file_em = fh.read()
    s = em.expand(file_em, **d)
    return s

def create_jenkins(jobname, config):
    import jenkins
    j = jenkins.Jenkins('http://hudson.willowgarage.com:8080', 'username', 'password')
    jobs = j.get_jobs()
    if jobname in [job['name'] for job in jobs]:
        j.reconfig_job(jobname, config)
    else:
        j.create_job(jobname, config)

def job_name(d):
    return "%(ROS_DISTRO)s_%(PACKAGE)s_sourcedeb" % d
if __name__ == "__main__":
    args = parse_options()
    d = dict(
    RELEASE_URI=args.release_uri,
    ROS_DISTRO=args.rosdistro,
    FQDN=args.fqdn,
    DISTROS=args.distros,
    CHILD_PROJECTS=[],
    PACKAGE=os.path.splitext(os.path.basename(args.release_uri))[0]
    )
    config_template = os.path.join(os.path.dirname(__file__), 'config.source.xml')
    command_template = os.path.join(os.path.dirname(__file__), 'sourcedebs.sh')

    
    command = expand(command_template, d)
    d['COMMAND'] = escape(command)
    config = expand(config_template, d)
    if args.commit:
        create_jenkins(job_name(d), config)
    else:
        print(config, "\n\n")
        print("Would have create a job %s " % job_name(d))
        print("--commit to do it for real.")
        
