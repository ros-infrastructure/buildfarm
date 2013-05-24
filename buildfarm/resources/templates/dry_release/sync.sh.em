#!/bin/bash -x

# exit if anything fails
set -o errexit

OS_PLATFORM=@(DISTRO)
ARCH=@(ARCH)
DISTRO_NAME=@(ROSDISTRO)
PACKAGES_FOR_SYNC=@(PACKAGES_FOR_SYNC)



echo $OS_PLATFORM
echo $ARCH
echo $DISTRO_NAME
echo $PACKAGES_FOR_SYNC



cd $WORKSPACE/buildfarm
. setup.sh


$WORKSPACE/buildfarm/scripts/count_ros_packages.py $DISTRO_NAME $OS_PLATFORM $ARCH --count $PACKAGES_FOR_SYNC
ssh rosbuild@@pub8 -- PYTHONPATH=/home/rosbuild/reprepro_updater/src python /home/rosbuild/reprepro_updater/scripts/prepare_sync.py /var/packages/ros-shadow-fixed/ubuntu -r $DISTRO_NAME -d $OS_PLATFORM -a $ARCH -u http://50.28.27.175/repos/building/ -c
# Sync source as well as binarys
ssh rosbuild@@pub8 -- PYTHONPATH=/home/rosbuild/reprepro_updater/src python /home/rosbuild/reprepro_updater/scripts/prepare_sync.py /var/packages/ros-shadow-fixed/ubuntu -r $DISTRO_NAME -d $OS_PLATFORM -a source -u http://50.28.27.175/repos/building/ -c

