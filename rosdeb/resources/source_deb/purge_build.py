#! /usr/bin/env python

"""
usage: %prog [args]
"""

import os, sys, string
from optparse import OptionParser
import subprocess
import roslib
import roslib.stacks
import shutil

def main(argv, stdout, environ):

  parser = OptionParser(__doc__.strip())
#  parser.add_option("-v","--var",action="store",type="string", dest="var",default="blah")

  (options, args) = parser.parse_args()

  if (args == 0):
    parser.error("Needs an argument")

  path = args[0]

  stacks = roslib.stacks.list_stacks_by_path(path)
  packages = roslib.stacks.expand_to_packages(stacks)[0]
  for p in packages:
    build_path = os.path.join(roslib.packages.get_pkg_dir(p), 'build')
    if os.path.exists(build_path):
      shutil.rmtree(build_path)

if __name__ == "__main__":
  main(sys.argv, sys.stdout, os.environ)
