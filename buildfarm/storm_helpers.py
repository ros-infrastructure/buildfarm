#!/usr/bin/env python

# Software License Agreement (BSD License)
#
# Copyright (c) 2014 Open Source Robotics Foundation
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
#  * Neither the name of Open Source Robotics Foundation nor the names of its
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
import sys
import yaml


def get_slave_servers(server_list):
    slave_servers = []
    for s in server_list:
        try:

            if 'storm.ros.org' in s['domain']:
                slave_servers.append(s)

            elif 'storm.willowgarage.com' in s['domain']:
                slave_servers.append(s)
            else:
                print >>sys.stderr, "%s not a slave: ignoring"%s['domain']
        except:
            print >>sys.stderr, "server doesn't have domain:", s
    return slave_servers


def get_default_catkin_debs_config():
    #stolen from buildfarm.jenkins_support
    import rospkg.environment
    return os.path.join(rospkg.environment.get_ros_home(), 'buildfarm', 'server.yaml')


def get_default_storm_config():
    import rospkg.environment
    return os.path.join(rospkg.environment.get_ros_home(), 'buildfarm', 'storm.yaml')


def load_config_from_file(server_config_file):
    if not os.path.isfile(server_config_file):
        raise RuntimeError("server config file [%s] does not exist" % server_config_file)

    with open(server_config_file) as f:
        server = yaml.load(f.read())
    return server
