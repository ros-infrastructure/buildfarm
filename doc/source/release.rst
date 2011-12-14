Release Script
==============

.. highlight:: ectosh


To release a catkin project, we will abuse `git-buildpackage <http://honk.sigxcpu.org/projects/git-buildpackage/manual-html/gbp.html>`_.

The script
----------

Make sure you have a local snap shot of the catkin project you would like to
release.  And also you should have a copy of the catkin-debs projects, and the
scripts folder in your path.

::
   
   git clone git://github.com/willowgarage/catkin-debs.git
   cd catkin-debs
   export PATH=`pwd`:$PATH

Now take a look at the release script help:

.. program-output:: catkin_release.py --help
   :prompt:


git repo
--------

For the first release of your catkin project, you need to create
a git repo. This repo has a few requirements.

1. It is publically accesible, with a git read only URL so that we can build it.
   e.g. ``git://github.com/willowgarage/catkin-debs.git``
#. You must have write access to the git repo in order to make a commit.
   On github, this means the ssh URL, e.g.
   ``git@github.com:willowgarage/catkin-debs.git``
#. Before the first commit, it must be absolutely empty to avoid conflicts.

Please email us your git repo readonly uri.

First release
-------------

For the purposes of this tutorial, I have a local project called foo_pkg.
I also created a brand new repo on github, called foo_pkg. Notice that
we are using the *pushable* uri for our git repo.

::

   % catkin_release.py git@github.com:mypackages/foo_pkg.git /path/to/foo_pkg fuerte --first_release
   Generating an upstream tarball --- /tmp/catkin_gbp/foo-pkg-0.1.0.tar.gz
   + git init
   Initialized empty Git repository in /tmp/catkin_gbp/foo_pkg/.git/
   + git remote add origin git@lou:/opt/repos/foo_pkg.git
   + git config --add remote.origin.push +refs/heads/*:refs/heads/*
   + git config --add remote.origin.push +refs/tags/*:refs/tags/*
   + git tag
   + git diff
   + git import-orig /tmp/catkin_gbp/foo-pkg-0.1.0.tar.gz
   ...
   
This will create a local gbp repo and create tags, and source debs.  If everything looks ok, push to your
git repo. Always start this with a clean working dir. If you fail to do this,
the script will poke at you to run the command.

::

   % catkin_release.py git@github.com:mypackages/foo_pkg.git /path/to/foo_pkg fuerte --first_release --push
   Generating an upstream tarball --- /tmp/catkin_gbp/foo-pkg-0.1.0.tar.gz
   please start from a bare working dir::
      rm -rf /tmp/catkin_gbp

If you are successful you should see something like:

::

   % catkin_release.py git@github.com:mypackages/foo_pkg.git /path/to/foo_pkg fuerte --first_release --push
   ...
   Counting objects: 31, done.
   Delta compression using up to 8 threads.
   Compressing objects: 100% (30/30), done.
   Writing objects: 100% (31/31), 4.78 KiB, done.
   Total 31 (delta 8), reused 0 (delta 0)
   To git@github.com:mypackages/foo_pkg.git
    * [new branch]      master -> master
    * [new branch]      upstream -> upstream
    * [new tag]         debian/ros_fuerte_0.1.0_lucid -> debian/ros_fuerte_0.1.0_lucid
    * [new tag]         debian/ros_fuerte_0.1.0_maverick -> debian/ros_fuerte_0.1.0_maverick
    * [new tag]         debian/ros_fuerte_0.1.0_natty -> debian/ros_fuerte_0.1.0_natty
    * [new tag]         debian/ros_fuerte_0.1.0_oneiric -> debian/ros_fuerte_0.1.0_oneiric
    * [new tag]         upstream/0.1.0 -> upstream/0.1.0
 
 
Subsequent releases
-------------------
 
Just get rid of the ``--first_release``

A practice run::

   % catkin_release.py git@github.com:mypackages/foo_pkg.git /path/to/foo_pkg fuerte

The real thing::

   % catkin_release.py git@github.com:mypackages/foo_pkg.git /path/to/foo_pkg fuerte --push

