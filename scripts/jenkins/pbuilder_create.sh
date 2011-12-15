#!/bin/bash
export ROS_PACKAGE_REPO=@(ROS_PACKAGE_REPO)
export ROS_DISTRO=@(ROS_DISTRO)
export distro=@(DISTRO)
export base=/var/cache/pbuilder-$ROS_DISTRO-$distro
export basetgz=$base/base.tgz
export aptconfdir=$base/apt-$ROS_DISTRO-$distro

sudo apt-get update
sudo apt-get install -y pbuilder
sudo mkdir -p $aptconfdir

echo "
deb http://archive.ubuntu.com/ubuntu $distro main restricted universe multiverse
deb $ROS_PACKAGE_REPO $distro main
deb-src $ROS_PACKAGE_REPO $distro main
" > sources.list
sudo mv sources.list $aptconfdir


sudo pbuilder create \
  --distribution $distro \
  --aptconfdir $aptconfdir \
  --basetgz $basetgz

sudo pbuilder --update

