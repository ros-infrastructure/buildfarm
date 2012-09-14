#!/bin/bash -x
OS_PLATFORM=@(DISTRO)
ARCH=@(ARCH)
STACK_NAME=@(STACK_NAME)
PACKAGE_NAME=@(PACKAGE)
DISTRO_NAME=@(ROSDISTRO)

echo $DISTRO_NAME
echo $STACK_NAME
echo $OS_PLATFORM
echo $ARCH

sudo apt-get install pbuilder git-core python-rospkg python-vcstools -y

cat > $WORKSPACE/build.bash << DELIM
source /opt/ros/cturtle/setup.sh
export ROS_PACKAGE_PATH=$WORKSPACE/ros_release:$WORKSPACE/release:$ROS_PACKAGE_PATH

#noupload while testing
rosrun rosdeb single_deb.py $DISTRO_NAME $STACK_NAME $OS_PLATFORM $ARCH
DELIM



if [ $STACK_NAME == 'metapackages' ] 
then

    bash $WORKSPACE/build.bash || true

    if [ -e $WORKSPACE/catkin-debs ]
    then
        rm -rf $WORKSPACE/catkin-debs
    fi

    git clone git://github.com/willowgarage/catkin-debs.git $WORKSPACE/catkin-debs -b master --depth 1

    cd $WORKSPACE/catkin-debs
    . setup.sh


    $WORKSPACE/catkin-debs/scripts/count_ros_packages.py $DISTRO_NAME $OS_PLATFORM $ARCH --count 100
    ssh rosbuild@pub8 -- PYTHONPATH=/home/rosbuild/reprepro_updater/src python /home/rosbuild/reprepro_updater/scripts/prepare_sync.py /var/packages/ros-shadow-fixed/ubuntu -r groovy -d oneiric -a amd64 -c
    
else
    bash $WORKSPACE/build.bash
fi