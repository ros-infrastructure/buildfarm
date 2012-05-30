#!/usr/bin/env python

from __future__ import print_function
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

import dependency_walker


URL_PROTOTYPE="https://raw.github.com/ros/rosdistro/master/releases/%s.yaml"

def parse_options():
    parser = argparse.ArgumentParser(
             description='Create a set of jenkins jobs '
             'for source debs and binary debs for a catkin package.')
    parser.add_argument('--fqdn', dest='fqdn',
           help='The source repo to push to, fully qualified something...',
           default='50.28.27.175')
    parser.add_argument(dest='rosdistro',
           help='The ros distro. electric, fuerte, galapagos')
    parser.add_argument('--distros', nargs='+',
           help='A list of debian distros. Default: %(default)s',
           default=[])
    parser.add_argument('--commit', dest='commit',
           help='Really?', action='store_true')
    parser.add_argument(dest='package_name',
           help='The name for the package')
    parser.add_argument('--repo-workspace', dest='repos', action='store', 
           help='A directory into which all the repositories will be checked out into.')
    parser.add_argument('--username',dest='username')
    parser.add_argument('--password',dest='password')
    args = parser.parse_args()
    if args.commit and ( not args.username or not args.password ):
        print('If you are going to commit, you need a username and pass.',file=sys.stderr)
        sys.exit(1)
    return parser.parse_args()

class Templates(object):
    template_dir = os.path.dirname(__file__)
    config_sourcedeb = os.path.join(template_dir, 'config.source.xml.em') #A config.xml template for sourcedebs.
    command_sourcedeb = os.path.join(template_dir, 'source_build.sh.em') #The bash script that the sourcedebs config.xml runs.
    config_bash = os.path.join(template_dir, 'config.bash.xml.em') #A config.xml template for something that runs a shell script
    command_binarydeb = os.path.join(template_dir, 'binary_build.sh.em') #builds binary debs.
    config_binarydeb = os.path.join(template_dir, 'config.binary.xml.em') #A config.xml template for something that runs a shell script

def expand(config_template, d):
    with open(config_template) as fh:
        file_em = fh.read()
    s = em.expand(file_em, **d)
    return s

def create_jenkins(jobname, config, username, password):
    try:
        j = jenkins.Jenkins('http://hudson.willowgarage.com:8080',
                            username, password)
        jobs = j.get_jobs()
        print("working on job", jobname)
        if jobname in [job['name'] for job in jobs]:
            j.reconfig_job(jobname, config)
        else:
            j.create_job(jobname, config)
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
        for arch in ('i386', 'amd64'):
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
    FQDN=fqdn,
    DISTROS=distros,
    CHILD_PROJECTS=child_projects,
    PACKAGE=package,
    ROSDISTRO=rosdistro,
    SHORT_PACKAGE_NAME= short_package_name
    )
    return  (sourcedeb_job_name(package), create_sourcedeb_config(d))

def doit(release_uri, package, distros, fqdn, job_graph, rosdistro, short_package_name, commit=False, username = None, password = None):

    #package = os.path.splitext(os.path.basename(release_uri))[0]

    binary_jobs = binarydeb_jobs(package, distros, fqdn, job_graph)
    child_projects = zip(*binary_jobs)[0] #unzip the binary_jobs tuple.
    source_job = sourcedeb_job(package, distros, fqdn, release_uri, child_projects, rosdistro, short_package_name)
    jobs = [source_job] + binary_jobs
    successful_jobs = []
    failed_jobs = []
    for job_name, config in jobs:
        if commit:
            if create_jenkins(job_name, config, username, password):
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


if __name__ == "__main__":
    args = parse_options()

    rd = rosdistro.Rosdistro(args.rosdistro)

    # backwards compatability
    repo_map = rd.repo_map 

    workspace = args.repos
    try:
        if not args.repos:
            workspace = tempfile.mkdtemp()
            
        (dependencies, pkg_by_url)  = dependency_walker.get_dependencies(workspace, repo_map['gbp-repos'], args.rosdistro)

    finally:
        if not args.repos:
            shutil.rmtree(workspace)

    # Figure out default distros.  Command-line arg takes precedence; if
    # it's not specified, then read targets.yaml.
    if args.distros:
        default_distros = args.distros
    else:
        default_distros = rosdistro.get_target_distros(args.rosdistro)

    # We take the intersection of repo-specific targets with default
    # targets.
    r = [x for x in repo_map['gbp-repos'] if 'name' in x and x['name'] == args.package_name]
    if len(r) != 1:
        print("No such package %s"%(args.package_name))
        sys.exit(1)
    r = r[0]
    if 'url' not in r or 'name' not in r:
        print("'name' and/or 'url' keys missing for repository %s; skipping"%(r))
        sys.exit(0)
    url = r['url']
    if url not in pkg_by_url:
        print("Repo %s is missing from the list; must have been skipped (e.g., for missing a stack.yaml)"%(r))
        sys.exit(0)
    if 'target' in r:
        if r['target'] == 'all':
            target_distros = default_distros
        else:
            target_distros = list(set(r['target']) & default_distros)
    else:
        target_distros = default_distros

    print ("Configuring %s for %s"%(r['url'], target_distros))


    results = doit(url, pkg_by_url[url], target_distros, args.fqdn, dependencies, args.rosdistro, args.package_name, args.commit, args.username, args.password)
    summarize_results(*results)
    if not args.commit:
        print("This was not pushed to the server.  If you want to do so use ",
              "--commit to do it for real.")
