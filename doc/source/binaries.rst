binaries
========
.. highlight:: ectosh

Take the source packages and build em...

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