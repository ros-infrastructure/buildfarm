#!/usr/bin/env python

from buildfarm.pbuilder_manager import PbuilderRunner
import tempfile

test_as = PbuilderRunner(root="/tmp/testdevel",
                         codename='precise',
                         arch='amd64',
                         image_number="devel3",
                         extrapackages="ca-certificates python python-yaml wget python-catkin-pkg python-rosdistro")

if not test_as.check_present():
    test_as.create()
#test_as.verify_up_to_date()


#apt-get install -y --force-yes ca-certificates python python-yaml wget python-catkin-pkg python-rosdistro

tf = tempfile.NamedTemporaryFile()
with open(tf.name, 'w') as fh:
    fh.write("""#!/bin/bash
whoami
pwd
wget https://github.com/ros-infrastructure/jenkins_scripts/archive/master.tar.gz
mkdir -p /tmp/jenkins_scripts
tar -xzf master.tar.gz -C /tmp/jenkins_scripts --strip-components=1
OS_PLATFORM=trusty /tmp/jenkins_scripts/devel hydro filters --workspace /tmp/workspace
""")

test_as.execute(tf.name, bindmounts="/tmp/workspace")
