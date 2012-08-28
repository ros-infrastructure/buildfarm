#!/usr/bin/env python

from __future__ import print_function
import em
import pkg_resources
import os
from xml.sax.saxutils import escape

import jenkins

from buildfarm.rosdep_support import resolve_rosdeps


class Templates(object):
    template_dir = os.path.dirname(__file__)
    config_devel = pkg_resources.resource_string('buildfarm', 'resources/templates/devel_job/config.devel.xml.em')  # A config.xml template for devel.
    config_scm_devel = {}
    config_scm_devel['git'] = pkg_resources.resource_string('buildfarm', 'resources/templates/devel_job/fragment.scm.git.devel.xml.em')
    config_scm_devel['hg'] = pkg_resources.resource_string('buildfarm', 'resources/templates/devel_job/fragment.scm.hg.devel.xml.em')
    config_scm_devel['svn'] = pkg_resources.resource_string('buildfarm', 'resources/templates/devel_job/fragment.scm.svn.devel.xml.em')
    command_devel = pkg_resources.resource_string('buildfarm', 'resources/templates/devel_job/devel_build.sh.em')  # The bash script that the devel config.xml runs.


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
    except jenkins.JenkinsException as ex:
        print('Failed to configure "%s" with error: %s' % (jobname, ex))
        return False


def create_devel_config(d):
    d['COMMAND'] = escape(expand(Templates.command_devel, d))
    return expand(Templates.config_devel, d)


def devel_job_name(rosdistro, packagename, distro, arch):
    return "ros-%(rosdistro)s-%(packagename)s_devel_%(distro)s_%(arch)s" % locals()


def devel_jobs(vcs_type, uri, version, package, stack, distros, rosdistro, fqdn, ros_package_repo="http://50.28.27.175/repos/building"):
    d = dict(
        URL=uri,
        VERSION=version,
        NAME=package,
    )
    scm_fragment = expand(Templates.config_scm_devel[vcs_type], d)

    notification_email = ' '.join([m.email for m in stack.maintainers])
    d = {
        'NAME': package,
        'SCM_FRAGMENT': scm_fragment,
        'XUNIT_XML_FRAGMENT': '',
        'NOTIFICATION_EMAIL': notification_email,
    }

    build_depends = [depends.name for depends in stack.build_depends]
    jobs = []
    for distro in [distros[1]]:  # for now only take one distro
        for arch in ['amd64']:  # removed 'i386' to build devel only on one arch
            job_name = devel_job_name(rosdistro, package, distro, arch)
            d['ARCH'] = arch
            d['BUILD_DEPENDS'] = ' '.join(build_depends)
            d['DISTRO'] = distro
            d['JOBNAME'] = job_name
            d['PLATFORM'] = distro
            d['ROSDISTRO'] = rosdistro
            config = create_devel_config(d)
            #print(config)
            jobs.append((job_name, config))
    return jobs


def doit(vcs_type, uri, version, package, stack, distros, fqdn, rosdistro, short_package_name, commit, jenkins_instance):

    #package = os.path.splitext(os.path.basename(uri))[0]

    jobs = devel_jobs(vcs_type, uri, version, package, stack, distros, rosdistro, fqdn)
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
