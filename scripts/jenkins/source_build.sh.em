#!/bin/bash
RELEASE_URI=@(RELEASE_URI)
FQDN=@(FQDN)
PACKAGE=@(PACKAGE)
ROSDISTRO=@(ROSDISTRO)
SHORT_PACKAGE_NAME=@(SHORT_PACKAGE_NAME)

sudo apt-get install -y git-buildpackage dput debhelper

if [ ! -e catkin-debs/.git ]
then
  git clone git://github.com/willowgarage/catkin-debs.git
else
  (cd catkin-debs && git clean -dfx && git reset --hard HEAD && git pull && git log -n1)
fi

rm -rf $WORKSPACE/output
rm -rf $WORKSPACE/workspace

catkin-debs/scripts/jenkins/catkin_build.py $RELEASE_URI $PACKAGE $ROSDISTRO $SHORT_PACKAGE_NAME --working $WORKSPACE/workspace --output $WORKSPACE/output --repo-fqdn $FQDN 