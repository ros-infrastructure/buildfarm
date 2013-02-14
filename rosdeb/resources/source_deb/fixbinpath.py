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
#  parser.add_option("-v","--var",action="store",type="string", dest="var",default="blah")

  (options, args) = parser.parse_args()

  if (len(args) < 3):
    print >> sys.stderr, 'Need to specify path, old_str, new_str'
    sys.exit(1)
    
  path = args[0]
  old_str = args[1]
  new_str = args[2]

  if len(old_str) < len(new_str):
    print >> sys.stderr, "New rpath must be shorter than old rpath"
    sys.exit(1)

  new_str_pad = new_str + chr(0)*(len(old_str)-len(new_str))

  print 'Replacing: %s'%(old_str)
  print '     with: %s'%(new_str_pad)

  with open(path, 'r') as f:
    binstr = f.read()

  binstr = binstr.replace(old_str,new_str_pad)

  with open(path, 'w') as f:
    f.write(binstr)


if __name__ == "__main__":
  main(sys.argv, sys.stdout, os.environ)
