Build Script
============

.. highlight:: ectosh


Given a gbp maintianed by the release script we would like to regenerate source
debs from it.

The script
----------

.. program-output:: catkin_build.py --help
   :prompt:

Usage
-----

This can be used either by the build farm or a curious developer to create
source debs from a git repo that is maintained by the release script.

The following will generate the latest source debs for catkin, for ros-fuerte::

  % catkin_build.py git://github.com/wg-debs/catkin.git fuerte
  ...
  Finished running lintian.
  % ls /tmp/catkin_debs/
  ros-fuerte-catkin_0.1.1-0lucid.diff.gz            ros-fuerte-catkin_0.1.1-0natty.dsc
  ros-fuerte-catkin_0.1.1-0lucid.dsc                ros-fuerte-catkin_0.1.1-0natty_source.build
  ros-fuerte-catkin_0.1.1-0lucid_source.build       ros-fuerte-catkin_0.1.1-0natty_source.changes
  ros-fuerte-catkin_0.1.1-0lucid_source.changes     ros-fuerte-catkin_0.1.1-0oneiric.diff.gz
  ros-fuerte-catkin_0.1.1-0maverick.diff.gz         ros-fuerte-catkin_0.1.1-0oneiric.dsc
  ros-fuerte-catkin_0.1.1-0maverick.dsc             ros-fuerte-catkin_0.1.1-0oneiric_source.build
  ros-fuerte-catkin_0.1.1-0maverick_source.build    ros-fuerte-catkin_0.1.1-0oneiric_source.changes
  ros-fuerte-catkin_0.1.1-0maverick_source.changes  ros-fuerte-catkin_0.1.1.orig.tar.gz
  ros-fuerte-catkin_0.1.1-0natty.diff.gz

Todo
----

* add signing to this step