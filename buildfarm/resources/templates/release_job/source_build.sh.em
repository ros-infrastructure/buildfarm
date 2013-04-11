#!/bin/bash
RELEASE_URI=@(RELEASE_URI)
FQDN=@(FQDN)
PACKAGE=@(PACKAGE)
ROSDISTRO=@(ROSDISTRO)
SHORT_PACKAGE_NAME=@(SHORT_PACKAGE_NAME)

sudo apt-get install -y git-buildpackage dput debhelper

if [ -e $WORKSPACE/buildfarm ]
then
  rm -rf $WORKSPACE/buildfarm
fi

git clone git://github.com/ros-infrastructure/buildfarm.git $WORKSPACE/buildfarm -b master --depth 1



cd $WORKSPACE/buildfarm 
. setup.sh



rm -rf $WORKSPACE/output
rm -rf $WORKSPACE/workspace

$WORKSPACE/buildfarm/scripts/generate_sourcedeb $RELEASE_URI $PACKAGE $ROSDISTRO $SHORT_PACKAGE_NAME --working $WORKSPACE/workspace --output $WORKSPACE/output --repo-fqdn $FQDN 