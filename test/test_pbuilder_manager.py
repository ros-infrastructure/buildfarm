#!/usr/bin/env python

import tempfile
import unittest
from buildfarm.pbuilder_manager import PbuilderRunner, PbuilderrcTempfile
import os
import shutil


class TestPbuilderrc(unittest.TestCase):

    def test_creation(self):
        pb_args = {}
        keys = ['BUILDPLACE', 'APTCACHE', 'CCACHEDIR',
                'BASETGZ']
        for k in keys:
            pb_args[k] = '/fake/%s' % k
        pb_args['AUTOCLEANAPTCACHE'] = 'yes'

        with PbuilderrcTempfile(pb_args) as pbrc:
            self.assertTrue(os.path.exists(pbrc))
            with open(pbrc, 'r') as fh:
                contents = fh.read()
        for k in keys:
            self.assertTrue("%s=" % k in contents, 'missing entry %s' % k)
        self.assertTrue("AUTOCLEANAPTCACHE=yes" in contents)


class TestPbuilderRunner(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.pass_script = os.path.join(self.tempdir,
                                        'hello_world.bash')
        with open(self.pass_script, 'w') as fh:
            fh.write("""#!/bin/bash

echo Hello World
exit 0
""")
            fh.flush()

        self.fail_script = os.path.join(self.tempdir,
                                        'fail_world.bash')
        with open(self.fail_script, 'w') as fh:
            fh.write("""#!/bin/bash

echo Hello World
echo Returning 1
exit 1
""")

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_simple(self):

        print "running pbuilder test"

        test_as = PbuilderRunner(root=self.tempdir,
                                 codename='trusty',
                                 arch='amd64',
                                 image_number=1)

        self.assertTrue(test_as.create())
        self.assertTrue(test_as.check_present())

        self.assertTrue(test_as.update())

        self.assertTrue(test_as.verify_up_to_date())

        self.assertTrue(test_as.execute(self.pass_script))
        self.assertFalse(test_as.execute(self.fail_script))

        #test_as.build('/tmp/src/ros-hydro-roscpp_1.9.50-0precise.dsc',
        #              '/tmp/output')


if __name__ == '__main__':
    unittest.main()
