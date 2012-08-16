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

import os
import sys

import rospkg.stack
from rospkg.os_detect import OS_UBUNTU
from rosdep2.catkin_support import get_catkin_view, resolve_for_apt, get_ubuntu_targets
from rosdep2..platforms.debian import APT_INSTALLER
#NOTE: this code is very similar to code in catkin-generate-distribution and rosrelease

def resolve_rosdeps(rosdep_keys, rosdistro_name, os_name, os_platform):
    """
    :raises: :exc:`rosdep2.catkin_support.ValidationFailed`
    :raises: :exc:`KeyError`
    :raises: :exc:`rosdep2.ResolutionError`
    """
    assert os_name == OS_UBUNTU
    assert os_platform
    assert type(rosdep_keys) == list

    # use the catkin_support module in rosdep2 as it does the same business

    # apt-install resolves data
    apt_installer = get_installer(APT_INSTALLER)
    # rosdep view is our view into the rosdep database
    rosdep_view = get_catkin_view(rosdistro_name, os_name, os_platform)

    # iterate through all our keys to resolve
    ubuntu_deps = set()
    for dep in rosdep_keys:
        resolved = resolve_for_apt(dep, rosdep_view, apt_installer, os_name, os_platform)
        ubuntu_deps.update(resolved)
    return list(ubuntu_deps)
