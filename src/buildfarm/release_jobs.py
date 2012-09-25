#!/usr/bin/env python

from __future__ import print_function
import em
import pkg_resources
import os
import sys
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET
import urllib
import urllib2
import yaml
import getpass
import datetime

from rospkg.distro import load_distro, distro_uri

from rosdistro import debianize_package_name

from . import repo

import jenkins


class Templates(object):
    template_dir = os.path.dirname(__file__)
    config_sourcedeb = pkg_resources.resource_string('buildfarm', 'resources/templates/release_job/config.source.xml.em')  # A config.xml template for sourcedebs.
    command_sourcedeb = pkg_resources.resource_string('buildfarm', 'resources/templates/release_job/source_build.sh.em')  # The bash script that the sourcedebs config.xml runs.
    command_binarydeb = pkg_resources.resource_string('buildfarm', 'resources/templates/release_job/binary_build.sh.em')  # builds binary debs.
    config_binarydeb = pkg_resources.resource_string('buildfarm', 'resources/templates/release_job/config.binary.xml.em')  # A config.xml template for something that runs a shell script
    config_dry_binarydeb = pkg_resources.resource_string('buildfarm', 'resources/templates/dry_release/config.xml.em')  # A config.xml template for something that runs a shell script
    command_dry_binarydeb = pkg_resources.resource_string('buildfarm', 'resources/templates/dry_release/build.sh.em')  # A config.xml template for something that runs a shell script


def expand(config_template, d):
    s = em.expand(config_template, **d)
    return s


def compute_missing(distros, fqdn, rosdistro):
    """ Compute what packages are missing from a repo based on the rosdistro files, both wet and dry. """

    URL_PROTOTYPE = 'https://raw.github.com/ros/rosdistro/master/releases/%s.yaml'


    repo_url = 'http://%s/repos/building' % fqdn

    print('Fetching "%s"' % (URL_PROTOTYPE % rosdistro))
    repo_map = yaml.load(urllib2.urlopen(URL_PROTOTYPE % rosdistro))


    # What ROS distro are we configuring?
    if 'release-name' not in repo_map:
        print('No "release-name" key in yaml file')
        sys.exit(1)
    if repo_map['release-name'] != rosdistro:
        print('release-name mismatch (%s != %s)' % (repo_map['release-name'], rosdistro))
        sys.exit(1)    
    if 'repositories' not in repo_map:
        print('No "repositories" key in yaml file')
    if 'type' not in repo_map or repo_map['type'] != 'gbp':
        print('Wrong type value in yaml file')
        sys.exit(1)

    # Figure out default distros.  Command-line arg takes precedence; if
    # it's not specified, then read targets.yaml.
    if distros:
        default_distros = distros
    else:
        print('Fetching "%s"' % (URL_PROTOTYPE % 'targets'))
        targets_map = yaml.load(urllib2.urlopen(URL_PROTOTYPE % 'targets'))
        my_targets = [x for x in targets_map if rosdistro in x]
        if len(my_targets) != 1:
            print('Must have exactly one entry for rosdistro "%s" in targets.yaml' % rosdistro)
            sys.exit(1)
        default_distros = my_targets[0][rosdistro]

    arches = ['amd64', 'i386']

    # We take the intersection of repo-specific targets with default
    # targets.
    missing = {}
    for short_package_name, r in repo_map['repositories'].items():
        if 'url' not in r:
            print('"url" key missing for repository "%s"; skipping' % r)
            continue
        url = r['url']
        if 'target' not in r or r['target'] == 'all':
            target_distros = default_distros
        else:
            target_distros = list(set(r['target']) & set(default_distros))

        #print ('Analyzing WET stack "%s" for "%s"' % (r['url'], target_distros))
        
        # todo check if sourcedeb is present with the right version
        deb_name = debianize_package_name(rosdistro, short_package_name)
        if not 'version' in r:
            print('"version" key missing for repository %s; skipping' % r)
            continue
        expected_version = r['version']
        if not expected_version:
            expected_version = ''
        
        missing[short_package_name] = []
        for d in target_distros:
            if not repo.deb_in_repo(repo_url, deb_name, expected_version+".*", d, arch='na', source=True):
                missing[short_package_name].append('%s_source' % d)
            for a in arches:
                if not repo.deb_in_repo(repo_url, deb_name, expected_version+".*", d, a):
                    missing[short_package_name].append('%s_%s' % (d, a))

                                               
        # if not trigger sourcedeb

        # else if binaries don't exist trigger them
        for d in target_distros:
            for a in arches:
                pass#missing[short_package_name] = ['source']
        


        

    #dry stacks
    # dry dependencies
    dist = load_distro(distro_uri(rosdistro))

    distro_arches = []
    for d in default_distros:
        for a in arches:
            distro_arches.append( (d, a) )

    for s in dist.stacks:
        #print ("Analyzing DRY job [%s]" % s)
        expected_version = dry_get_stack_version(s, dist)
        
        # sanitize undeclared versions for string substitution
        if not expected_version:
            expected_version = ''
        missing[s] = []
        # for each distro arch check if the deb is present. If not trigger the build. 
        for (d, a) in distro_arches:
            if not repo.deb_in_repo(repo_url, debianize_package_name(rosdistro, s), expected_version+".*", d, a):
                missing[s].append( '%s_%s' % (d, a) )


    return missing


# dry dependencies
def dry_get_stack_info(stackname, version):
    y = urllib.urlopen('https://code.ros.org/svn/release/download/stacks/%(stackname)s/%(stackname)s-%(version)s/%(stackname)s-%(version)s.yaml' % locals() )
    return yaml.load(y.read())
                 

def dry_get_stack_version(stackname, rosdistro_obj):
    if not stackname in rosdistro_obj.stacks:
        raise Exception("Stack %s not in distro %s" % (stackname, rosdistro_obj.release_name))
    st = rosdistro_obj.stacks[stackname]
    return st.version


def dry_get_versioned_dependency_tree(rosdistro):
    d = load_distro(distro_uri(rosdistro))    
    dependency_tree = {}
    versions = {}
    for s in d.stacks:
        version = d.stacks[s].version
        versions[s] = version
        yaml_info = dry_get_stack_info(s, version)
        if 'depends' in yaml_info:
            dependency_tree[s] = yaml_info['depends']
        else:
            dependency_tree[s] = []
    return dependency_tree, versions

def dry_generate_jobgraph(rosdistro):
    if rosdistro == 'backports':
        return {}

    (stack_depends, versions) = dry_get_versioned_dependency_tree(rosdistro)
    
    jobgraph = {}
    for key, val in stack_depends.iteritems():
        jobgraph[debianize_package_name(rosdistro, key)] = [debianize_package_name(rosdistro, p) for p in val ]
    return jobgraph


    

def compare_configs(a, b):
    """Return True if the configs are the same, except the
    description, else False"""
    aroot = ET.fromstring(a)
    broot = ET.fromstring(b)

    return compare_xml_children(aroot, broot)

def compare_xml_text_and_attribute(a, b):
    if not a.text == b.text:
        #print("text %s does not match %s" %( a.text, b.text) )
        return False
    if not a.attrib == b.attrib:
        #print("attrib %s does not match %s" %(a.attrib, b.attrib ) )
        return False
    return True


def compare_xml_children(a, b):
    for child in a:
        tag = child.tag
        if tag == 'description':
            continue

        b_found = b.findall(tag)
        if not b_found:
            print("Failed to find tags %s" % tag)
            return False

        #If multple of the same tags try them all
        match_found = False
        for b_child in b_found:
            match_found = compare_xml_children(b_child, child) and compare_xml_text_and_attribute(b_child, child)
            if match_found:
                continue

        if not match_found:
            #print("Found %d tags %s, none matched" % (len(b_found), tag ))
            return False
        
    return True
    

def create_jenkins_job(jobname, config, jenkins_instance):
    try:
        jobs = jenkins_instance.get_jobs()
        print("working on job", jobname)
        if jobname in [job['name'] for job in jobs]:
            remote_config = jenkins_instance.get_job_config(jobname)
            if not compare_configs(remote_config, config):
                jenkins_instance.reconfig_job(jobname, config)
            else:
                print("Skipping %s as config is the same" % jobname)

        else:
            jenkins_instance.create_job(jobname, config)
        return True
    except jenkins.JenkinsException as ex:
        print('Failed to configure "%s" with error: %s' % (jobname, ex))
        return False


def sourcedeb_job_name(packagename):
    return "%(packagename)s_sourcedeb" % locals()


def create_sourcedeb_config(d):
    #Create the bash script the runs inside the job
    #need the command to be safe for xml.
    d['COMMAND'] = escape(expand(Templates.command_sourcedeb, d))
    d['USERNAME'] = getpass.getuser()
    d['TIMESTAMP'] = datetime.datetime.now()
    return expand(Templates.config_sourcedeb, d)


def create_binarydeb_config(d):
    d['USERNAME'] = getpass.getuser()
    d['TIMESTAMP'] = datetime.datetime.now()
    d['COMMAND'] = escape(expand(Templates.command_binarydeb, d))
    return expand(Templates.config_binarydeb, d)

def create_dry_binarydeb_config(d):
    d['COMMAND'] = escape(expand(Templates.command_dry_binarydeb, d))
    d['USERNAME'] = getpass.getuser()
    d['TIMESTAMP'] = datetime.datetime.now()
    return expand(Templates.config_dry_binarydeb, d)


def binarydeb_job_name(packagename, distro, arch):
    return "%(packagename)s_binarydeb_%(distro)s_%(arch)s" % locals()


def calc_child_jobs(packagename, distro, arch, jobgraph):
    children = []
    if jobgraph:
        for package, deps in jobgraph.iteritems():
            if packagename in deps:
                children.append(binarydeb_job_name(package, distro, arch))
    return children



def add_dependent_to_dict(packagename, jobgraph):
    dependents = {}
    if jobgraph:
        if packagename in jobgraph:
            dependents = jobgraph[packagename]
    return dependents



def dry_binarydeb_jobs(stackname, rosdistro, distros, jobgraph):
    package = debianize_package_name(rosdistro, stackname)
    d = dict(
        PACKAGE=package,
        ROSDISTRO=rosdistro,
        STACK_NAME=stackname
    )
    jobs = []
    for distro in distros:
        for arch in ('i386', 'amd64'):  # removed 'armel' as it as qemu debootstrap is segfaulting
            d['ARCH'] = arch
            d['DISTRO'] = distro

            d["CHILD_PROJECTS"] = calc_child_jobs(package, distro, arch, jobgraph)
            d["DEPENDENTS"] = "True"
            config = create_dry_binarydeb_config(d)
            #print(config)
            job_name = binarydeb_job_name(package, distro, arch)
            jobs.append((job_name, config))
            #print ("config of %s is %s" % (job_name, config))
    return jobs

def binarydeb_jobs(package, distros, fqdn, jobgraph, ros_package_repo="http://50.28.27.175/repos/building"):
    d = dict(
        DISTROS=distros,
        FQDN=fqdn,
        ROS_PACKAGE_REPO=ros_package_repo,
        PACKAGE=package
    )
    jobs = []
    for distro in distros:
        for arch in ('i386', 'amd64'):  # removed 'armel' as it as qemu debootstrap is segfaulting
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
    SHORT_PACKAGE_NAME=short_package_name
    )
    return  (sourcedeb_job_name(package), create_sourcedeb_config(d))


def dry_doit(package, distros,  rosdistro, jobgraph, commit, jenkins_instance):

    jobs = dry_binarydeb_jobs(package, rosdistro, distros, jobgraph)

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


def doit(release_uri, package, distros, fqdn, job_graph, rosdistro, short_package_name, commit, jenkins_instance):

    #package = os.path.splitext(os.path.basename(release_uri))[0]

    binary_jobs = binarydeb_jobs(package, distros, fqdn, job_graph)
    child_projects = zip(*binary_jobs)[0]  # unzip the binary_jobs tuple
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
    print('=' * 80)
    jobs = set(unattempted_jobs).union(set(successful_jobs)).union(set(failed_jobs))
    print ('Summary: %d jobs configured.  Listed below.' % len(jobs))
    print ('Unexecuted: %d' % len(unattempted_jobs))
    for job_name in unattempted_jobs:
        print ("  %s" % job_name)
    print ('Successful: %d' % len(successful_jobs))
    for job_name in successful_jobs:
        print ("  %s" % job_name)
    print ('Failed: %d' % len(failed_jobs))
    for job_name in failed_jobs:
        print ("  %s" % job_name)
    print('=' * 80)
