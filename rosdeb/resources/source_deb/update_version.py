#! /usr/bin/env python

"""
usage: %prog [args]
"""

import os, sys, string
from optparse import OptionParser
import time

def main(argv, stdout, environ):

  parser = OptionParser(__doc__.strip())

  (options, args) = parser.parse_args()

  if (len(args) != 1):
    parser.error("Usage: ./update_version.py <CHANGELOG>")

  build_version = "%d"%time.mktime(time.gmtime())

  with open(args[0],'r') as f:
    changelog = f.read()
    
  changelog = changelog.replace('$BUILD_VERSION', build_version)

  print changelog

if __name__ == "__main__":
  main(sys.argv, sys.stdout, os.environ)
