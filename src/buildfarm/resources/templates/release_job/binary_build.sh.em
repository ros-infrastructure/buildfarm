#!/bin/bash -x

#stop on error
set -o errexit

ROS_REPO_FQDN=@(FQDN)
ROS_PACKAGE_REPO=@(ROS_PACKAGE_REPO)
PACKAGE=@(PACKAGE)
distro=@(DISTRO)
arch=@(ARCH)
base=/var/cache/pbuilder-$distro-$arch


aptconffile=$WORKSPACE/apt.conf

#increment this value if you have changed something that will invalidate base tarballs. #TODO this will need cleanup eventually.
basetgz_version=5

rootdir=$base/apt-conf-$basetgz_version

basetgz=$base/base-$basetgz_version.tgz
output_dir=$WORKSPACE/output
work_dir=$WORKSPACE/work



if [ $arch == armel ]
then
    mirror=http://ports.ubuntu.com/ubuntu-ports
    debootstrap_type='qemu-debootstrap'
else
    mirror=http://aptproxy.willowgarage.com/us.archive.ubuntu.com/ubuntu
    debootstrap_type='debootstrap'
fi


sudo apt-get update
sudo apt-get install -y pbuilder python-empy python-argparse debhelper # todo move to server setup, or confirm it's there
sudo apt-get install -y qemu-arm-static # on precise it's now qemu-user-static I believe

if [ -e $WORKSPACE/catkin-debs ]
then
  rm -rf $WORKSPACE/catkin-debs
fi

git clone git://github.com/willowgarage/catkin-debs.git $WORKSPACE/catkin-debs -b master --depth 1


cd $WORKSPACE/catkin-debs
. setup.sh

#setup the cross platform apt environment
# using sudo since this is shared with pbuilder and if pbuilder is interupted it will leave a sudo only lock file.  Otherwise sudo is not necessary. 
# And you can't chown it even with sudo and recursive 
sudo PYTHONPATH=$PYTHONPATH $WORKSPACE/catkin-debs/scripts/setup_apt_root.py $distro $arch $rootdir --local-conf-dir $WORKSPACE --mirror $mirror

# Check if this package exists, and call update which will update the cache, following calls don't need to update
#if [ -e $WORKSPACE/catkin-debs/scripts/jenkins/apt_env/check_package_built.py $rootdir $PACKAGE -u ]
#then
#    echo "no need to run this deb already exists"
#    exit 0
#fi

# check precondition that all dependents exist, don't check if no dependencies
@[if DEPENDENTS]
sudo $WORKSPACE/catkin-debs/scripts/assert_package_dependencies_present.py $rootdir $aptconffile  $PACKAGE -u
@[end if]

sudo rm -rf $output_dir
mkdir -p $output_dir

sudo rm -rf $work_dir
mkdir -p $work_dir
cd $work_dir




sudo apt-get update -c $aptconffile -o Apt::Architecture=$arch
sudo apt-get source $PACKAGE -c $aptconffile

# extract version number from the dsc file
version=`ls *.dsc | sed s/${PACKAGE}_// | sed s/$distro\.dsc//`
echo "package name ${PACKAGE} version ${version}"


# Setup the pbuilder environment if not existing, or update
if [ ! -e $basetgz ] || [ ! -s $basetgz ] 
then
  #make sure the base dir exists
  sudo mkdir -p $base
  #create the base image
  sudo pbuilder create \
    --distribution $distro \
    --aptconfdir $rootdir/etc/apt \
    --basetgz $basetgz \
    --architecture $arch \
    --mirror $mirror \
    --keyring /etc/apt/trusted.gpg \
    --debootstrap $debootstrap_type \
    --debootstrapopts --arch=$arch \
    --debootstrapopts --keyring=/etc/apt/trusted.gpg
else
  sudo pbuilder --update --basetgz $basetgz
fi


# hooks for changing the binary debs to be timestamped
mkdir -p hooks

echo "#!/bin/bash -ex
echo \`env\`
cd /tmp/buildd/*/
apt-get install devscripts -y
prevversion=\`dpkg-parsechangelog | grep Version | awk '{print \$2}'\`
debchange -D $distro -v \$prevversion-\`date +%Y%m%d-%H%M-%z\` 'Time stamping.'
cat debian/changelog
" >> hooks/A50stamp
chmod +x hooks/A50stamp

#  --binary-arch even if "any" type debs produce arch specific debs
sudo pbuilder  --build \
    --basetgz $basetgz \
    --buildresult $output_dir \
    --debbuildopts \"-b\" \
    --hookdir hooks \
    *.dsc



# invalidate all binary packages which will depend on this package

cat > invalidate.py << DELIM
#!/usr/bin/env python
import paramiko
cmd = "( flock 200; /usr/bin/reprepro -b /var/www/repos/building -T deb -V removefilter $distro \"Package (% ros-* ), Architecture (== $arch ), ( Depends (% *$PACKAGE[, ]* ) | Depends (% *$PACKAGE ) )\" && /usr/bin/reprepro -b /var/www/repos/building -T deb -V removefilter $distro \"Package (== $PACKAGE ), Architecture (== $arch ) \" ) 200>/var/www/repos/building/lock"
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('$ROS_REPO_FQDN', username='rosbuild')
stdin, stdout, stderr = ssh.exec_command(cmd)
print "Invalidation results:", stdout.readlines()
ssh.close()
DELIM

echo "invalidation script contents for debugging:"
cat invalidate.py
python invalidate.py

# push the new deb, config followed by execution
echo """
[debtarget]
method                  = scp
fqdn                    = $ROS_REPO_FQDN
incoming                = /var/www/repos/building/queue/$distro
run_dinstall            = 0
post_upload_command     = ssh rosbuild@@$ROS_REPO_FQDN -- '( flock 200; /usr/bin/reprepro -b /var/www/repos/building --ignore=emptyfilenamepart -V processincoming $distro ) 200>/var/www/repos/building/lock'
""" > $output_dir/dput.cf

dput -u -c $output_dir/dput.cf debtarget $output_dir/*$DISTRO*.changes
