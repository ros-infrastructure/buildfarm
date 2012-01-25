#!/bin/bash -x

#stop on error
set -o errexit

ROS_REPO_FQDN=@(FQDN)
ROS_PACKAGE_REPO=@(ROS_PACKAGE_REPO)
PACKAGE=@(PACKAGE)
ROS_DISTRO=@(ROS_DISTRO)
distro=@(DISTRO)
arch=@(ARCH)
DEBPACKAGE=ros-$ROS_DISTRO-@(PACKAGE.replace('_','-'))
base=/var/cache/pbuilder-$ROS_DISTRO-$distro-$arch


aptconffile=$WORKSPACE/apt.conf

#increment this value if you have changed something that will invalidate base tarballs. #TODO this will need cleanup eventually.
basetgz_version=0

rootdir=$base/apt-conf-$basetgz_version

basetgz=$base/base-$basetgz_version.tgz
output_dir=$WORKSPACE/output
work_dir=$WORKSPACE/work

sudo apt-get update
sudo apt-get install -y pbuilder python-empy python-argparse debhelper # todo move to server setup, or confirm it's there

if [ ! -e catkin-debs/.git ]
then
  git clone git://github.com/willowgarage/catkin-debs.git
else
  (cd catkin-debs && git pull)
fi

#setup the cross platform apt environment
# using sudo since this is shared with pbuilder and if pbuilder is interupted it will leave a sudo only lock file.  Otherwise sudo is not necessary.
sudo $WORKSPACE/catkin-debs/scripts/jenkins/apt_env/setup_apt_root.py $distro $arch $rootdir --local-conf-dir $WORKSPACE

# Check if this package exists, and call update which will update the cache, following calls don't need to update
#if [ -e $WORKSPACE/catkin-debs/scripts/jenkins/apt_env/check_package_built.py $rootdir $DEBPACKAGE -u ]
#then
#    echo "no need to run this deb already exists"
#    exit 0
#fi

# check precondition that all dependents exist, don't check if no dependencies
@[if DEPENDENTS]
sudo $WORKSPACE/catkin-debs/scripts/jenkins/apt_env/assert_package_dependencies_present.py $rootdir $aptconffile  $DEBPACKAGE -u
@[end if]

sudo rm -rf $output_dir
mkdir -p $output_dir

sudo rm -rf $work_dir
mkdir -p $work_dir
cd $work_dir




sudo apt-get update -c $aptconffile
sudo apt-get source $DEBPACKAGE -c $aptconffile

sudo rm -rf $basetgz

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
    --architecture $arch
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
debchange -v \$prevversion-\`date +%Y%m%d-%H%M-%z\` 'Time stamping.'
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
cmd = "/usr/bin/reprepro -b /var/www/repos/building -T deb -V removefilter $distro \"Package (% ros-* ), Architecture (== $arch ), ( Depends (% *$DEBPACKAGE,* ) | Depends (% *$DEBPACKAGE ) )\" "
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('$ROS_REPO_FQDN', username='rosbuild')
stdin, stdout, stderr = ssh.exec_command(cmd)
print "Invalidation results:", stdout.readlines()
ssh.close()
DELIM

echo "invalidation script contents for debugging:"
cat invalidate.py
# commented out for now due to spurious failures. NOT ABI SAVE python invalidate.py

# push the new deb, config followed by execution
echo "
[debtarget]
method                  = scp
fqdn                    = $ROS_REPO_FQDN
incoming                = /var/www/repos/building/queue/$distro
run_dinstall            = 0
post_upload_command     = ssh rosbuild@@$ROS_REPO_FQDN -- /usr/bin/reprepro -b /var/www/repos/building --ignore=emptyfilenamepart -V processincoming $distro
" > $output_dir/dput.cf

dput -u -c $output_dir/dput.cf debtarget $output_dir/*$DISTRO*.changes
