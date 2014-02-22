# Software License Agreement (BSD License)
#
# Copyright (c) 2012, Willow Garage, Inc.
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
import difflib
import em
import os
import jenkins
import yaml
import xml.etree.ElementTree as ElementTree

# TODO Push this up to python-jenkins


class InvalidJenkinsConfig(Exception):
    pass


class JenkinsConfig(object):

    def __init__(self, url, username=None, password=None):
        """
        :raises: :exc:`InvalidJenkinsConfig`
        """
        self.url = url
        self.username = username
        self.password = password

        if username is None:
            raise InvalidJenkinsConfig("no jenkins username configured; cannot create CI jobs")
        if password is None:
            raise InvalidJenkinsConfig("no jenkins password configured; cannot create CI jobs")


def JenkinsConfig_to_handle(server_config):
    return jenkins.Jenkins(server_config.url, server_config.username, server_config.password)


def get_default_catkin_debs_config():
    import rospkg.environment
    return os.path.join(rospkg.environment.get_ros_home(), 'buildfarm', 'server.yaml')


def load_server_config_file(server_config_file):
    """
    :raises: :exc:`InvalidJenkinsConfig`
    :returns: :class:`JenkinsConfig` instance
    """
    # TODO: typed exception
    if not os.path.isfile(server_config_file):
        raise RuntimeError("server config file [%s] does not exist" % server_config_file)

    with open(server_config_file) as f:
        server = yaml.load(f.read())
    server_keys = server.keys()
    if not ('url' in server_keys and 'username' in server_keys and 'password' in server_keys):
        raise InvalidJenkinsConfig("Server config file does not contains 'url', 'username' and 'password'  all of which are required. %s" % server_config_file)
    return JenkinsConfig(server['url'], server['username'], server['password'])


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


def expand(config_template, d):
    s = em.expand(config_template, **d)
    return s
