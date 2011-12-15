binaries
========
.. highlight:: ectosh


Take the source packages and build em...

See this tutorial for some nice starting places: https://wiki.ubuntu.com/PackagingGuide/Complete

pbuilder
--------

For example using `pbuilder <http://www.netfort.gr.jp/~dancer/software/pbuilder-doc/pbuilder-doc.html>`_

::
  
  % sudo pbuilder --build /tmp/catkin_debs/ros-fuerte-catkin_0.1.1-0oneiric.dsc

Or anything else...

speedy local testing
--------------------

To test if the source debs are buildable on your machine, not in a chroot,
try the following recipe::
  
  % dpkg-source -x ros-fuerte-catkin_0.1.1-0oneiric.dsc
  % cd ros-fuerte-catkin-0.1.1/
  % dpkg-buildpackage -rfakeroot -uc -b

If something fails, you can just play directly in the unpacked debian package.
Use the distro that you have on your machine.

apt-get
-------
If you have some source debs in an apt repo, e.g. reprepro, ppa.

Here are some steps to build something from a source deb using apt::

   % apt-get build-dep ros-fuerte-common-msgs
   The following NEW packages will be installed:
   ros-fuerte-catkin ros-fuerte-gencpp ros-fuerte-genmsg ros-fuerte-genpy ros-fuerte-std-msgs
   ...
   Setting up ros-fuerte-std-msgs (3.4.5-20111204-2300-0800~oneiric) ...
   % apt-get source -b ros-fuerte-common-msgs
   ...
   dpkg-buildpackage: binary only upload (no source included)

LVM
---
https://help.ubuntu.com/community/SbuildLVMHowto
