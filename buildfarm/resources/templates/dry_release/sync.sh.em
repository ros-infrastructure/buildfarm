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
ssh rosbuild@@repos.ros.org -- PYTHONPATH=/home/rosbuild/reprepro_updater/src python /home/rosbuild/reprepro_updater/scripts/prepare_sync.py /var/www/repos/ros-shadow-fixed/ubuntu -r $DISTRO_NAME -d $OS_PLATFORM -a $ARCH -u file:/var/www/repos/building/ -c

@[if DISTRO == DISTROS[0] and ARCH == ARCHES[0] ]
@{distro_args = ["-d %s" % d for d in DISTROS] }
# Sync source as well as binarys
ssh rosbuild@@repos.ros.org -- PYTHONPATH=/home/rosbuild/reprepro_updater/src python /home/rosbuild/reprepro_updater/scripts/prepare_sync.py /var/www/repos/ros-shadow-fixed/ubuntu -r @(ROSDISTRO) @(" ".join(distro_args)) -a source -u file:/var/www/repos/building/ -c

@[end if]

ssh rosbuild@repos.ros.org -- bash /home/rosbuild/push_keys/push_fixed.bash