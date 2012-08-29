#!/bin/bash -x
OS_PLATFORM=@(DISTRO)
ARCH=@(ARCH)
STACK_NAME=@(PACKAGE)
DISTRO_NAME=@(ROSDISTRO)

echo $DISTRO_NAME
echo $STACK_NAME
echo $OS_PLATFORM
echo $ARCH

sudo apt-get install pbuilder git-core -y

cat > $WORKSPACE/build.bash << DELIM
source /opt/ros/cturtle/setup.sh
export ROS_PACKAGE_PATH=$WORKSPACE/ros_release:$WORKSPACE/release:$ROS_PACKAGE_PATH

#noupload while testing
rosrun rosdeb single_deb.py $DISTRO_NAME $STACK_NAME $OS_PLATFORM $ARCH --force --besteffort --noupload
DELIM

bash $WORKSPACE/build.bash