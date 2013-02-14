#! /usr/bin/env python

"""
usage: %prog [args]
"""

import os, sys, string
from optparse import OptionParser
import subprocess

def main(argv, stdout, environ):

  parser = OptionParser(__doc__.strip())
  parser.add_option("-t","--test",action="store_true", dest="test",default=False,
                    help="A testing flag")

  (options, args) = parser.parse_args()

  if (len(args) < 3):
    print >> sys.stderr, 'Need to pass args: path old_path new_path'
    sys.exit(1)
 
  path = args[0]
  old_path = args[1]
  new_path = args[2]

  if len(old_path) < len(new_path):
    print >> sys.stderr, "New path must be shorter than old rpath"
    sys.exit(1)

  print 'Replacing: %s'%old_path
  print '     with: %s'%new_path

  for root, dirs, files in os.walk(path):
    for f in files:

      if f[-3:] == '.pc':

        with open(os.path.join(root,f), 'r') as ff:
          pcstr = ff.read()

        pcstr = pcstr.replace(old_path,new_path)

        with open(os.path.join(root,f), 'w') as ff:
          ff.write(pcstr)
        


if __name__ == "__main__":
  main(sys.argv, sys.stdout, os.environ)
