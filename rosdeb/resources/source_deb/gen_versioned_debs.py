#! /usr/bin/env python

"""
usage: %prog [args]
"""

import os
import sys
from optparse import OptionParser
import subprocess

try:
  # backwards-compatible for Fuerte changes
  import rospkg
  rosstack = rospkg.RosStack()
  def depends_1(stack):
    return rosstack.get_depends(stack, implicit=False)
except ImportError:
  import roslib.rospack
  depends_1 = roslib.rospack.rosstack_depends_1
  
def main(argv, stdout, environ):

  parser = OptionParser(__doc__.strip())

  (options, args) = parser.parse_args()

  if (len(args) != 2):
    parser.error("Usage: <distro> <stack>")
    
  distro,stack = args

  deps = []
  
  for stk in depends_1(stack):
    version = None
    debname = "ros-%s-%s"%(distro, stk.replace('_','-'))
    cmd = subprocess.Popen(['dpkg', '-s', debname], stdout=subprocess.PIPE)
    o,e = cmd.communicate()
    if cmd.returncode != 0:
      raise "Could not find dependency version number"
    for l in o.splitlines():
      if l.startswith('Version:'):
        version = l.split()[1].strip()
    if version:
      deps.append("%s (= %s)"%(debname,version))
    else:
      raise "Could not find dependency version number"

  print "rosstack:Depends="+", ".join(deps)


if __name__ == "__main__":
  main(sys.argv, sys.stdout, os.environ)
