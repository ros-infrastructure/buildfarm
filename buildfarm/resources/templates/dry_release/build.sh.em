#!/bin/bash -x

# exit if anything fails
set -o errexit

ROS_REPO_FQDN=@(FQDN)
OS_PLATFORM=@(DISTRO)
ARCH=@(ARCH)
STACK_NAME=@(STACK_NAME)
PACKAGE_NAME=@(PACKAGE)
DISTRO_NAME=@(ROSDISTRO)
PACKAGES_FOR_SYNC=@(PACKAGES_FOR_SYNC)



echo $DISTRO_NAME
echo $STACK_NAME
echo $OS_PLATFORM
echo $ARCH



# Get latest buildfarm repo
if [ -e $WORKSPACE/buildfarm ]
then
  rm -rf $WORKSPACE/buildfarm
fi

git clone git://github.com/ros-infrastructure/buildfarm.git $WORKSPACE/buildfarm -b master --depth 1

cd $WORKSPACE/buildfarm
. setup.sh


# Building package
single_deb.py $DISTRO_NAME $STACK_NAME $OS_PLATFORM $ARCH --fqdn $ROS_REPO_FQDN

