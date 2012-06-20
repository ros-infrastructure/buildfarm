#!/usr/bin/env python

from distutils.core import setup

#import sys
#sys.path.insert(0, 'src')

#from buildfarm import __version__

setup(name='buildfarm',
      version='0.0.1',
      packages=['buildfarm'],
      package_dir = {'buildfarm':'src/buildfarm'},
      scripts = ['scripts/setup_apt_root.py',
                 'scripts/list_all.py'],
      package_data = {'buildfarm': ['resources/templates/*.em', 'resources/templates/*/*']},
      install_requires = ['vcstools', 'rospkg'],
      author = "Tully Foote", 
      author_email = "tfoote@willowgarage.com",
      url = "http://www.ros.org/wiki/",
      download_url = "http://pr.willowgarage.com/downloads/buildfarm/", 
      keywords = ["ROS"],
      classifiers = [
        "Programming Language :: Python", 
        "License :: OSI Approved :: BSD License" ],
      description = "ROS package library", 
      long_description = """\
A library for interacting with the Catkin buildfarm.
""",
      license = "BSD"
      )
