#!/bin/bash -x

# exit if anything fails
set -o errexit

OS_PLATFORM=@(DISTRO)
ARCH=@(ARCH)
STACK_NAME=@(STACK_NAME)
PACKAGE_NAME=@(PACKAGE)
DISTRO_NAME=@(ROSDISTRO)



echo $DISTRO_NAME
echo $STACK_NAME
echo $OS_PLATFORM
echo $ARCH

sudo apt-get update
sudo apt-get install pbuilder git-core python-rospkg python-vcstools -y


# Building package
source /opt/ros/cturtle/setup.sh
export ROS_PACKAGE_PATH=$WORKSPACE/ros_release:$WORKSPACE/release:$ROS_PACKAGE_PATH

@[if IS_METAPACKAGES]
# do not exit if this fails
set +o errexit
@[end if]

rosrun rosdeb single_deb.py $DISTRO_NAME $STACK_NAME $OS_PLATFORM $ARCH

@[if IS_METAPACKAGES]

# exit if anything fails
set -o errexit

if [ -e $WORKSPACE/catkin-debs ]
then
    rm -rf $WORKSPACE/catkin-debs
fi

git clone git://github.com/willowgarage/catkin-debs.git $WORKSPACE/catkin-debs -b master --depth 1

cd $WORKSPACE/catkin-debs
. setup.sh

$WORKSPACE/catkin-debs/scripts/count_ros_packages.py $DISTRO_NAME $OS_PLATFORM $ARCH --count 350
ssh rosbuild@@pub8 -- PYTHONPATH=/home/rosbuild/reprepro_updater/src python /home/rosbuild/reprepro_updater/scripts/prepare_sync.py /var/packages/ros-shadow-fixed/ubuntu -r $DISTRO_NAME -d $OS_PLATFORM -a $ARCH -u http://50.28.27.175/repos/building/ -c


@[end if]


