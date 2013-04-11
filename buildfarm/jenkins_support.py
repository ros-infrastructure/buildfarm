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

import os
import jenkins
import yaml

# TODO Push this up to python-jenkins

class InvalidJenkinsConfig(Exception): pass


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
    #TODO: typed exception
    if not os.path.isfile(server_config_file):
        raise RuntimeError("server config file [%s] does not exist"%(server_config_file))

    with open(server_config_file) as f:
        server = yaml.load(f.read())
    server_keys = server.keys()
    if not ('url' in server_keys and 'username' in server_keys and 'password' in server_keys):
        raise InvalidJenkinsConfig("Server config file does not contains 'url', 'username' and 'password'  all of which are required. %s"%server_config_file)
    return JenkinsConfig(server['url'], server['username'], server['password'])
