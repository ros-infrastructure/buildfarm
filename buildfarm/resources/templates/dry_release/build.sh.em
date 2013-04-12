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
@[if IS_METAPACKAGES]
# do not exit if this fails
set +o errexit
@[end if]

single_deb.py $DISTRO_NAME $STACK_NAME $OS_PLATFORM $ARCH --fqdn $ROS_REPO_FQDN

@[if IS_METAPACKAGES]

# exit if anything fails
set -o errexit

$WORKSPACE/buildfarm/scripts/count_ros_packages.py $DISTRO_NAME $OS_PLATFORM $ARCH --count $PACKAGES_FOR_SYNC
ssh rosbuild@@pub8 -- PYTHONPATH=/home/rosbuild/reprepro_updater/src python /home/rosbuild/reprepro_updater/scripts/prepare_sync.py /var/packages/ros-shadow-fixed/ubuntu -r $DISTRO_NAME -d $OS_PLATFORM -a $ARCH -u http://50.28.27.175/repos/building/ -c
# Sync source as well as binarys
ssh rosbuild@@pub8 -- PYTHONPATH=/home/rosbuild/reprepro_updater/src python /home/rosbuild/reprepro_updater/scripts/prepare_sync.py /var/packages/ros-shadow-fixed/ubuntu -r $DISTRO_NAME -d $OS_PLATFORM -a source -u http://50.28.27.175/repos/building/ -c

@[end if]
