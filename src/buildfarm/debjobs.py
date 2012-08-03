#!/usr/bin/env python

from __future__ import print_function

import pkg_resources
import em
import os
import sys
from xml.sax.saxutils import escape
import argparse

import yaml
import tempfile
import shutil
import urllib2

import rosdistro

import jenkins



class Templates(object):
    template_dir = os.path.dirname(__file__)
    config_sourcedeb = pkg_resources.resource_string('buildfarm', 'resources/templates/debjob/config.source.xml.em') #A config.xml template for sourcedebs.
    command_sourcedeb = pkg_resources.resource_string('buildfarm', 'resources/templates/debjob/source_build.sh.em') #The bash script that the sourcedebs config.xml runs.
    command_binarydeb = pkg_resources.resource_string('buildfarm', 'resources/templates/debjob/binary_build.sh.em') #builds binary debs.
    config_binarydeb = pkg_resources.resource_string('buildfarm', 'resources/templates/debjob/config.binary.xml.em') #A config.xml template for something that runs a shell script

def expand(config_template, d):
    s = em.expand(config_template, **d)
    return s

def create_jenkins_job(jobname, config, jenkins_instance):
    try:
        jobs = jenkins_instance.get_jobs()
        print("working on job", jobname)
        if jobname in [job['name'] for job in jobs]:
            jenkins_instance.reconfig_job(jobname, config)
        else:
            jenkins_instance.create_job(jobname, config)
        return True
    except jenkins.JenkinsException, ex:
        print("Failed to configure %s with error: %s"%(jobname, ex))
        return False

def sourcedeb_job_name(packagename):
    return "%(packagename)s_sourcedeb" % locals()

def create_sourcedeb_config(d):
    #Create the bash script the runs inside the job
    #need the command to be safe for xml.
    d['COMMAND'] = escape(expand(Templates.command_sourcedeb, d))
    return expand(Templates.config_sourcedeb, d)

def create_binarydeb_config(d):
    d['COMMAND'] = escape(expand(Templates.command_binarydeb, d))
    return expand(Templates.config_binarydeb, d)


def binarydeb_job_name(packagename, distro, arch):
    return "%(packagename)s_binarydeb_%(distro)s_%(arch)s" % locals()

def calc_child_jobs(packagename, distro, arch, jobgraph):
    children = []
    if jobgraph:
        for package,deps in jobgraph.iteritems():
            if packagename in deps:
                children.append(binarydeb_job_name(package, distro, arch))
    return children

def add_dependent_to_dict(packagename, jobgraph):
    dependents = {}
    if jobgraph:
        if packagename in jobgraph:
            dependents =  jobgraph[packagename]

    return dependents

def binarydeb_jobs(package, distros, fqdn, jobgraph, ros_package_repo="http://50.28.27.175/repos/building"):
    d = dict(
        DISTROS=distros,
        FQDN=fqdn,
        ROS_PACKAGE_REPO=ros_package_repo,
        PACKAGE=package
    )
    jobs = []
    for distro in distros:
        for arch in ('i386', 'amd64', 'armel'):
            d['ARCH'] = arch
            d['DISTRO'] = distro
            d["CHILD_PROJECTS"] = calc_child_jobs(package, distro, arch, jobgraph)
            d["DEPENDENTS"] = add_dependent_to_dict(package, jobgraph)
            config = create_binarydeb_config(d)
            #print(config)
            job_name = binarydeb_job_name(package, distro, arch)
            jobs.append((job_name, config))
    return jobs

def sourcedeb_job(package, distros, fqdn, release_uri, child_projects, rosdistro, short_package_name):
    d = dict(
    RELEASE_URI=release_uri,
    RELEASE_BRANCH='master',
    FQDN=fqdn,
    DISTROS=distros,
    CHILD_PROJECTS=child_projects,
    PACKAGE=package,
    ROSDISTRO=rosdistro,
    SHORT_PACKAGE_NAME= short_package_name
    )
    return  (sourcedeb_job_name(package), create_sourcedeb_config(d))

def doit(release_uri, package, distros, fqdn, job_graph, rosdistro, short_package_name, commit, jenkins_instance):

    #package = os.path.splitext(os.path.basename(release_uri))[0]

    binary_jobs = binarydeb_jobs(package, distros, fqdn, job_graph)
    child_projects = zip(*binary_jobs)[0] #unzip the binary_jobs tuple.
    source_job = sourcedeb_job(package, distros, fqdn, release_uri, child_projects, rosdistro, short_package_name)
    jobs = [source_job] + binary_jobs
    successful_jobs = []
    failed_jobs = []
    for job_name, config in jobs:
        if commit:
            if create_jenkins_job(job_name, config, jenkins_instance):
                successful_jobs.append(job_name)
            else:
                failed_jobs.append(job_name)
    unattempted_jobs = [job for (job, config) in jobs if job not in successful_jobs and job not in failed_jobs]

    return (unattempted_jobs, successful_jobs, failed_jobs)

def summarize_results(unattempted_jobs, successful_jobs, failed_jobs):
    print("="*80)
    jobs = set(unattempted_jobs).union(set(successful_jobs)).union(set(failed_jobs))
    print ("Summary: %d jobs configured.  Listed below." % len(jobs))
    print ("Unexecuted: %d"%len(unattempted_jobs))
    for job_name in unattempted_jobs:
        print ("  %s" % job_name)
    print ("Successful: %d"%len(successful_jobs))
    for job_name in successful_jobs:
        print ("  %s" % job_name)
    print ("Failed: %d"%len(failed_jobs))
    for job_name in failed_jobs:
        print ("  %s" % job_name)
    print("="*80)


