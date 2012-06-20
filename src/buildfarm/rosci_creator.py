# Software License Agreement (BSD License)
#
# Copyright (c) 2011, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import print_function

import os
import pkg_resources
import sys
import yaml

DISPATH_SH_URI = 'https://raw.github.com/willowgarage/buildfarm/master/dispatch.sh'
CATKIN_BUILDER = 'rosci-catkin-cmake-builder.sh'

def get_resource_stream(name):
    fullname = os.path.join('resources/templates/rosci', name)
    if not pkg_resources.resource_exists('buildfarm', fullname):
        raise RuntimeError("cannot locate template fragment: %s"%(fullname))
    return pkg_resources.resource_stream('buildfarm', fullname)


def VcsConfig_to_scm_fragment(vcs_config, local_name, branch='devel'):
    # have to set local_name, source, and version variables
    uri, version = vcs_config.get_branch(branch, anonymous=True)
    vcs_type = vcs_config.type
    source = uri
    
    if vcs_type == 'hg':
        version = version or 'default'
    elif vcs_type == 'svn':
        if version is not None:
            source = "%s@%s"%(uri, version)
    elif vcs_type == 'git':
        version = version or 'master'
    f = get_resource_stream('scm-%s-fragment.xml'%vcs_type)
    return f.read()%locals()

class JobConfig(object):

    def __init__(self, name, job_type, vcs_config, email, label, params):
        self.name = name
        self.type = job_type
        self.email = email
        self.label = label
        self.vcs_config = vcs_config
        self.params = params
        
def load_jobs_from_list(data):
    jobs = []
    assert type(data) == list, data
    for job_data in data:
        assert type(job_data) == dict
        jobs.append(create_JobConfig_from_dict(job_data))
    return jobs
    
def load_jobs_from_file(filename):
    with open(filename) as f:
        return load_jobs_from_list(yaml.load(f))
    
def create_JobConfig_from_dict(d):
    import rospkg.distro # for vcs-config parsing
    try:
        job_type = d['type']
        assert job_type in ['catkin']
        
        name = d['name']
        
        email = d['email']
        label = d['label']

        # no substitutions in this version (yet)
        rules = d['vcs_config']
        params = d['params']
        vcs_config = rospkg.distro.load_vcs_config(rules, lambda x: x)

        return JobConfig(name, job_type, vcs_config, email, label, params)
        
    except KeyError as e:
        raise KeyError("Missing required job config key %s\nData: %s"%(str(e), d))
    
def create_jenkins_config_xml(job_config, rosdistro_name, os_name, os_platform, arch):
    # temporary until we support more configs
    assert job_config.type == 'catkin'
    stack_build_depends = job_config.params['stack-build-depends']
    profiles = job_config.params['profiles']
    assert profiles == ['devel'], profiles

    from xml.sax.saxutils import escape
    local_name = job_config.name
    scm = VcsConfig_to_scm_fragment(job_config.vcs_config, local_name, 'devel')
    label = job_config.label

    # convert to fragment
    notification_email = job_config.email

    image_type = 'all'

    env_vars = {
        'ROSDISTRO_NAME': rosdistro_name,
        'OS_NAME' : os_name,
        'OS_PLATFORM' : os_platform,
        'UBUNTU_DISTRO' : os_platform, #backwards-compat
        'IMAGETYPE': image_type,
        'ARCH' : arch, 
        'STACK_NAME' : job_config.name,
        'STACK_BUILD_DEPENDS': ' '.join(stack_build_depends),
        'JOB_TYPE' : job_config.type,
        'SCRIPT' : CATKIN_BUILDER,
        }

    shell_fragment = "# THIS BUILD RECIPE WAS AUTOGENERATED\n\n"
    for k,v in env_vars.iteritems():
        shell_fragment += "export %s=\"%s\"\n"%(k,v)
    shell_fragment += """
wget %s -O $WORKSPACE/build.sh
bash $WORKSPACE/build.sh
"""%(DISPATH_SH_URI)

    local_name = job_config.name
    scm_fragment = VcsConfig_to_scm_fragment(job_config.vcs_config, local_name)

    #TODO
    xunit_xml_fragment = ''
    
    f = get_resource_stream('config.xml')
    config_template = f.read()
    
    return config_template%locals()

# SKETCH OF WHAT WE WANT TO DO IN THE SHELL
# export APT_DEPENDENCIES=`rosci-catkin-depends $ROSDISTRO_NAME $OS_NAME $OS_PLATFORM $STACK_BUILD_DEPENDS`

def get_jenkins_job_name(project_name, rosdistro_name, os_name, os_platform, arch):
    return 'ci-devel-%(project_name)s-%(rosdistro_name)s-%(os_name)s-%(os_platform)s-%(arch)s'%(locals())

def create_ci_job(jenkins_handle, job_config, rosdistro_name, os_name, os_platform, arch, fake):
    job_name = job_config.name
    jenkins_url = jenkins_handle.server
    print("""Job configuration:
     * Job name: %(job_name)s
     * Jenkins URL: %(jenkins_url)s
     * ROS distro: %(rosdistro_name)s
     * OS: %(os_name)s
     * OS release: %(os_platform)s
     """%(locals()))
    
    config_xml = create_jenkins_config_xml(job_config, rosdistro_name, os_name, os_platform, arch)
    jenkins_job_name = get_jenkins_job_name(job_name, rosdistro_name, os_name, os_platform, arch)

    if fake:
        print(config_xml)
        print(jenkins_job_name)
        return
    
    if jenkins_handle.job_exists(jenkins_job_name):
        print("reconfigure existing job [%s]"%(jenkins_job_name))
        jenkins_handle.reconfig_job(jenkins_job_name, config_xml)
    else:
        print("creating job [%s]"%(jenkins_job_name))
        jenkins_handle.create_job(jenkins_job_name, config_xml)
    
def process_jobs(jobs_data, jenkins_handle, rosdistro_name, fake):
    from rospkg.os_detect import OS_UBUNTU

    #TODO: parameterize, use rosdep2.rep3 targets as well
    for job_config in jobs_data:
        for os_name in [OS_UBUNTU]:
            for os_platform in ['lucid']:
                for arch in ['amd64']:
                    create_ci_job(jenkins_handle, job_config, rosdistro_name, os_name, os_platform, arch, fake)
