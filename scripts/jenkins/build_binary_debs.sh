#!/bin/bash
export RELEASE_URI=@(RELEASE_URI)
export ROS_DISTRO=@(ROS_DISTRO)
export FQDN=@(FQDN)
export distro=@(DISTRO)
export base=/var/cache/pbuilder-$ROS_DISTRO-$distro
export basetgz=$base/base.tgz
export aptconfdir=$base/apt-$ROS_DISTRO-$distro
export PACKAGE=$(PACKAGE)
rm -rf $WORKSPACE/output
mkdir -p $WORKSPACE/output

rm -rf $WORKSPACE/working
mkdir -p $WORKSPACE/working
cd $WORKSPACE/working

sudo apt-get update
apt-get source $PACKAGE

sudo pbuilder --update --basetgz $basetgz
sudo pbuilder --build --basetgz $basetgz --buildresult $WORKSPACE/output --debbuildopts "-b" *.dsc

ls $WORKSPACE/output

echo "
[uploadhost]
method                  = scp
fqdn                    = $FQDN
incoming                = /var/www/repos/building/queue/$distro
run_dinstall            = 0
post_upload_command     = ssh rosbuild@@$FQDN -- /usr/bin/reprepro -b /var/www/repos/building -V processincoming distro
" > $WORKSPACE/output/dput.cf

dput -u -c $WORKSPACE/output/dput.cf uploadhost $WORKSPACE/output/*$distro*.changes
