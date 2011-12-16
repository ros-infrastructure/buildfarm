
Brainstorm
==========
A highlevel brainstorm... Likely out of date.

notes 12/10/2011
----------------


Pipeline steps
++++++++++++++
1.  Make a release ...
2.  Import the release into a git-buildpackage repo, /repos/PACKAGE.git
    These will have some tag convention that is easy to create a package per debian/ubuntu
    distro.::

        debian/ros_electric_0.1.1_lucid
        debian/ros_electric_0.1.1_maverick
        debian/ros_electric_0.1.1_natty
        debian/ros_electric_0.1.1_oneiric
        upstream/0.1.1
       
   Most likely will have one repo per ros distro, so that merging is simple.

3.  A job that monitors the *gbp* is triggered and builds source debs. ``*.dsc``
    This will use *gbp* to checkout the git repo, and create the source debs.
    ``dput`` can then be used to upload the source debs to a reprepro source repo.

4.  binaries are created from the source repo::

       $ apt-get build-dep ros-fuerte-common-msgs
       The following NEW packages will be installed:
         ros-fuerte-catkin ros-fuerte-gencpp ros-fuerte-genmsg ros-fuerte-genpy ros-fuerte-std-msgs
       ...
       Setting up ros-fuerte-std-msgs (3.4.5-20111204-2300-0800~oneiric) ...
       $ apt-get source -b ros-fuerte-common-msgs 
       ...
       dpkg-buildpackage: binary only upload (no source included)
   
   If apt-get is used to build the package, then it is assumed to be inside a changeroot of the
   platform that the binary is desired for.
   ``dput`` is used again to upload these to reprepro for distribution to the masses.


Reasoning
+++++++++

Git buildpackage

* Git buildpackage will be a nice interface for debugging the source deb packaging.
  See the debian maintainers and how much they use git buildpackage repos
  -- http://anonscm.debian.org/gitweb/
* This gives a nice history of our source debs, and it can be used to conveniently regenerate them
  if need be.
* It could be a way of people injecting releases in a secure fashion. You push a release and ask me
  to pull from your repo.

dput of source debs as the input to the build farm

* a standard way to upload debian source packages and binaries
* works well with launchpad for testing and community based repos.
* A clean breakage of concerns for our build farm, once its in as a source deb we can build it
  using apt, sbuild, pbuilder, etc...
* for testing the debs, devs can get the sources from the source deb repo, without waiting for
  build farm.
  
  
notes 12/14/2011
----------------

It may be useful to add a few more pieces of info to the **stack.yaml**

- source vcs uri
- vcs type
- release repo
- docs public location uri
- docs build type - sphinx, doxygen, make, ...

Using just a stack.yaml, and an upstream tar ball we can build source debs... OpenCV, pcl...

would be good to sign the source debs with a gpg key on the build server

A set of git repos for catkin-ros

::

   git clone git@github.com:willowgarage/catkin-debs.git
   git clone git@github.com:willowgarage/catkin.git
   git clone git@github.com:ros/genmsg.git
   git clone git@github.com:ros/gencpp.git
   git clone git@github.com:ros/genpy.git
   git clone git@github.com:ros/genpy.git
   git clone git@github.com:ros/genpybindings.git
   git clone git@github.com:ros/std_msgs.git
   git clone git@github.com:ros/roscpp_core.git

*python-em* should **not** be necessary inside the stack.yaml...

Document what variables are defined for ``*.em`` templates.  