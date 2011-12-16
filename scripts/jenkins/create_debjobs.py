#!/usr/bin/env python

from __future__ import print_function
import em
import os
from xml.sax.saxutils import escape
import argparse
import jenkins

def parse_options():
    parser = argparse.ArgumentParser(description='Create a set of jenkins jobs for source debs and binary debs for a catkin package.')
    parser.add_argument('--fqdn', dest='fqdn',
            help='The source repo to push to, fully qualified something or other...', default='50.28.27.175')
    parser.add_argument(dest='rosdistro', help='The ros distro. electric, fuerte, galapagos')
    parser.add_argument('--distros', nargs='+',
            help='A list of debian distros. Default: %(default)s',
            default=['lucid', 'natty', 'oneiric'])
    parser.add_argument('--commit', dest='commit', help='Really?', action='store_true')
    parser.add_argument(dest='release_uri',
            help='A release repo uri..')
    return parser.parse_args()

class Templates(object):
    template_dir = os.path.dirname(__file__)
    config_sourcedeb = os.path.join(template_dir, 'config.source.xml') #A config.xml template for sourcedebs.
    command_sourcedeb = os.path.join(template_dir, 'source_build.sh') #The bash script that the sourcedebs config.xml runs.
    config_bash = os.path.join(template_dir, 'config.bash.xml') #A config.xml template for something that runs a shell script
    command_binarydeb = os.path.join(template_dir, 'binary_build.sh') #builds binary debs.

def expand(config_template, d):
    with open(config_template) as fh:
        file_em = fh.read()
    s = em.expand(file_em, **d)
    return s

def create_jenkins(jobname, config):
    j = jenkins.Jenkins('http://hudson.willowgarage.com:8080', 'username', 'password')
    jobs = j.get_jobs()
    if jobname in [job['name'] for job in jobs]:
        j.reconfig_job(jobname, config)
    else:
        j.create_job(jobname, config)

def sourcedeb_job_name(d):
    return "%(ROS_DISTRO)s_%(PACKAGE)s_sourcedeb" % d

def create_sourcedeb_config(d):
    #Create the bash script the runs inside the job
    #need the command to be safe for xml.
    d['COMMAND'] = escape(expand(Templates.command_sourcedeb, d))
    return expand(Templates.config_sourcedeb, d)

def create_binarydeb_config(d):
    d['COMMAND'] = escape(expand(Templates.command_binarydeb, d))
    return expand(Templates.config_bash, d)

def binarydeb_job_name(d):
    return "%(ROS_DISTRO)s_%(PACKAGE)s_binarydeb_%(DISTRO)s_%(ARCH)s" % d

def binarydeb_jobs(package, rosdistro, distros, fqdn, ros_package_repo="http://50.28.27.175/repos/building"):
    d = dict(
        ROS_DISTRO=rosdistro,
        DISTROS=distros,
        FQDN=fqdn,
        ROS_PACKAGE_REPO=ros_package_repo,
        PACKAGE=package
    )
    jobs = []
    for distro in distros:
        for arch in ('i386', 'amd64'):
            d['ARCH'] = arch
            d['DISTRO'] = distro
            config = create_binarydeb_config(d)
            job_name = binarydeb_job_name(d)
            jobs.append((job_name, config))
    return jobs

def sourcedeb_job(package, rosdistro, distros, fqdn, release_uri, child_projects):
    d = dict(
    RELEASE_URI=release_uri,
    ROS_DISTRO=rosdistro,
    FQDN=fqdn,
    DISTROS=distros,
    CHILD_PROJECTS=child_projects,
    PACKAGE=package
    )
    return  (sourcedeb_job_name(d), create_sourcedeb_config(d))

def doit():
    args = parse_options()
    package = os.path.splitext(os.path.basename(args.release_uri))[0]

    binary_jobs = binarydeb_jobs(package, args.rosdistro, args.distros, args.fqdn)
    child_projects = zip(*binary_jobs)[0] #unzip the binary_jobs tuple.
    source_job = sourcedeb_job(package, args.rosdistro, args.distros, args.fqdn, args.release_uri, child_projects)
    jobs = [source_job] + binary_jobs
    for job_name, config in jobs:
        if args.commit:
            create_jenkins(job_name, config)
        else:
            print(config, "\n\n*****************************")
            print("Would have created job: %s " % job_name)
            print("--commit to do it for real.")

if __name__ == "__main__":
    doit()
