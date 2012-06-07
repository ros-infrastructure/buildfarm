#!/bin/bash
RELEASE_URI=@(RELEASE_URI)
FQDN=@(FQDN)
PACKAGE=@(PACKAGE)
ROSDISTRO=@(ROSDISTRO)
SHORT_PACKAGE_NAME=@(SHORT_PACKAGE_NAME)

sudo apt-get install -y git-buildpackage dput debhelper

if [ ! -e catkin-debs/.git ]
then
  git clone git://github.com/willowgarage/catkin-debs.git -b library
else
  (cd catkin-debs && git checkout library && git clean -dfx && git reset --hard HEAD && git pull && git log -n1)
fi

. catkin-debs/setup.sh


rm -rf $WORKSPACE/output
rm -rf $WORKSPACE/workspace

catkin-debs/scripts/generate_sourcedeb $RELEASE_URI $PACKAGE $ROSDISTRO $SHORT_PACKAGE_NAME --working $WORKSPACE/workspace --output $WORKSPACE/output --repo-fqdn $FQDN 