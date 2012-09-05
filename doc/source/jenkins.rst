jenkins configuration
=====================

Jenkins is used as the build farm for building debians from catkin based projects.

Have a look under ``scripts/jenkins``

::
   git clone git://github.com/willowgarage/catkin-debs.git
   export PATH=`pwd`/catkin-debs/scripts/jenkins:$PATH

create_all.py
-----------------

This script creates a few jobs and commits them to a jenkins server.


.. program-output:: create_all.py --help
   :prompt:
