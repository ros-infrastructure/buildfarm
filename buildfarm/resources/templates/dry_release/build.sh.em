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


staging_dir=$WORKSPACE/staging_dir
rm -rf $staging_dir
mkdir -p $staging_dir

# Building package
single_deb.py $DISTRO_NAME $STACK_NAME $OS_PLATFORM $ARCH --fqdn $ROS_REPO_FQDN -d $staging_dir --noupload


@[if PACKAGE != "metapackges"]

# Upload invalidate and add to the repo
UPLOAD_DIR=/tmp/upload/${PACKAGE_NAME}_${OS_PLATFORM}_$ARCH

ssh rosbuild@@$ROS_REPO_FQDN -- rm -rf $UPLOAD_DIR
ssh rosbuild@@$ROS_REPO_FQDN -- mkdir -p $UPLOAD_DIR
scp -r $staging_dir/results/* rosbuild@@$ROS_REPO_FQDN:$UPLOAD_DIR
ssh rosbuild@@$ROS_REPO_FQDN -- PYTHONPATH=/home/rosbuild/reprepro_updater/src python /home/rosbuild/reprepro_updater/scripts/include_folder.py -d $OS_PLATFORM -a $ARCH -f $UPLOAD_DIR -p $PACKAGE_NAME -c --delete --invalidate

@[end if]