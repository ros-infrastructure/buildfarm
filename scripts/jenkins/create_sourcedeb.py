#!/usr/bin/env python

from __future__ import print_function
import em
import os
from urllib import urlencode
from xml.sax.saxutils import escape

def common_options(parser):
    parser.add_argument('--fqdn', dest='fqdn',
            help='The source repo to push to, fully qualified something or other...', default='50.28.27.175')
    parser.add_argument(dest='rosdistro', help='The ros distro. electric, fuerte, galapagos')
    parser.add_argument('--distros', nargs='+',
            help='A list of debian distros. Default: %(default)s',
            default=['lucid', 'natty', 'oneiric'])
    parser.add_argument('--commit', dest='commit', help='Really?', action='store_true')

def parse_options():
    import argparse
    parser = argparse.ArgumentParser(description='Create a jenkins job for building sourcedebs.')
    parser.add_argument(dest='release_uri',
            help='A release repo uri..')
    common_options(parser)
    return parser.parse_args()

class Templates(object):
    template_dir = os.path.dirname(__file__)
    config_template = os.path.join(template_dir, 'config.source.xml') #A config.xml template for sourcedebs.
    command_template = os.path.join(template_dir, 'sourcedebs.sh') #The bash script that the sourcedebs config.xml runs.
    config_bash_template = os.path.join(template_dir, 'config.bash.xml') #A config.xml template for something that runs a shell script

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

def create_config(d):
    #Create the bash script the runs inside the job
    #need the command to be safe for xml.
    d['COMMAND'] = escape(expand(Templates.command_template, d))
    #Now expand the configuration xml
    return expand(Templates.config_template, d)


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
    config = create_config(d)
    job_name = job_name(d)
    if args.commit:
        create_jenkins(job_name, config)
    else:
        print(config, "\n\n*****************************")
        print("Would have created job: %s " % job_name)
        print("--commit to do it for real.")
