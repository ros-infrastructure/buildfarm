#!/usr/bin/env python

from __future__ import print_function

from buildfarm.pbuilder_manager import PbuilderRunner
import tempfile
import unittest
import os.path
import shutil

print("This test needs sudo to setup a chroot. User mode chroot development appears to have stopped so we can't use that.")

class TestPbuilderRunner(unittest.TestCase):

    def setUp(self):
        self.test_root = tempfile.mkdtemp()

        def tearDown(self):
            shutil.rmtree(self.test_root, ignore_errors=True)


    def test_create(self):
        test_as = PbuilderRunner(root=self.test_root,
                                 codename='precise',
                                 arch='amd64',
                                 image_number="devel3",
                                 extrapackages="ca-certificates python python-yaml wget python-catkin-pkg python-rosdistro")
        
        self.assertFalse(test_as.check_present())
        self.assertTrue(test_as.create())
        self.assertTrue(test_as.check_present())

#test_as.verify_up_to_date()


#apt-get install -y --force-yes ca-certificates python python-yaml wget python-catkin-pkg python-rosdistro
        
        workspace = tempfile.mkdtemp()
        test_output = os.path.join(workspace, 'pwd.txt')
        tf = tempfile.NamedTemporaryFile()
        with open(tf.name, 'w') as fh:
            fh.write("""#!/bin/bash
set -o errexit
whoami
pwd > %s
dpkg -l ca-certificates python python-yaml wget python-catkin-pkg python-rosdistro
""" % test_output)

        self.assertTrue(test_as.execute(tf.name, bindmounts=workspace))

        self.assertTrue(os.path.exists(test_output))
        shutil.rmtree(workspace, ignore_errors=True)

