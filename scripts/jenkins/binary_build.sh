#!/bin/bash
export ROS_REPO_FQDN=@(FQDN)
export ROS_PACKAGE_REPO=@(ROS_PACKAGE_REPO)
export PACKAGE=@(PACKAGE)
export ROS_DISTRO=@(ROS_DISTRO)
export distro=@(DISTRO)
export arch=@(ARCH)
export DEBPACKAGE=ros-$ROS_DISTRO-@(PACKAGE.replace('_','-'))
export base=/var/cache/pbuilder-$ROS_DISTRO-$distro-$arch
export aptconfdir=$base/apt-conf
export aptstatedir=$base/apt-state
export basetgz=$base/base.tgz
export output_dir=$WORKSPACE/output
export work_dir=$WORKSPACE/work

sudo apt-get update
sudo apt-get install -y pbuilder

sudo mkdir -p $aptconfdir
sudo mkdir -p $aptconfdir/apt.conf.d
sudo mkdir -p $aptconfdir/preferences.d
sudo mkdir -p $aptstatedir/lists/partial


sudo rm -rf $output_dir
mkdir -p $output_dir

sudo rm -rf $work_dir
mkdir -p $work_dir
cd $work_dir

echo "
deb http://archive.ubuntu.com/ubuntu $distro main restricted universe multiverse
deb $ROS_PACKAGE_REPO $distro main
deb-src $ROS_PACKAGE_REPO $distro main
" > sources.list
sudo cp sources.list $aptconfdir

if [ ! -e $basetgz ]
then
  sudo pbuilder create \
    --distribution $distro \
    --aptconfdir $aptconfdir \
    --basetgz $basetgz \
    --architecture $arch 
else
  sudo pbuilder --update --basetgz $basetgz
fi

echo "
Dir::Etc $aptconfdir;
Dir::State $aptstatedir;
" > apt.conf

sudo apt-get update -c $work_dir/apt.conf
sudo apt-get source $DEBPACKAGE -c $work_dir/apt.conf

sudo pbuilder  --build \
    --basetgz $basetgz \
    --buildresult $output_dir \
    --binary-arch \  # even if "any" type debs produce arch specific debs
    --debbuildopts \"-b\" \
    *.dsc

echo "
[debtarget]
method                  = scp
fqdn                    = $ROS_REPO_FQDN
incoming                = /var/www/repos/building/queue/$distro
run_dinstall            = 0
post_upload_command     = ssh rosbuild@@$ROS_REPO_FQDN -- /usr/bin/reprepro -b /var/www/repos/building -V processincoming $distro
" > $output_dir/dput.cf

dput -u -c $output_dir/dput.cf debtarget $output_dir/*$DISTRO*.changes
