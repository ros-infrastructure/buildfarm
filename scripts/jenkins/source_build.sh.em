RELEASE_URI=@(RELEASE_URI)
ROS_DISTRO=@(ROS_DISTRO)
FQDN=@(FQDN)

sudo apt-get install -y git-buildpackage dput

if [ ! -e catkin-debs/.git ]
then
  git clone git://github.com/willowgarage/catkin-debs.git
else
  (cd catkin-debs && git pull)
fi

rm -rf $WORKSPACE/output

catkin-debs/scripts/catkin_build.py $RELEASE_URI $ROS_DISTRO --working $WORKSPACE/workspace --output $WORKSPACE/output
ls $WORKSPACE/output

for distro in @(' '.join(DISTROS))
do
    echo "
[uploadhost]
method                  = scp
fqdn                    = $FQDN
incoming                = /var/www/repos/building/queue/$distro
run_dinstall            = 0
post_upload_command     = ssh rosbuild@@$FQDN -- /usr/bin/reprepro -b /var/www/repos/building -V processincoming $distro
" > $WORKSPACE/output/dput.cf
    dput -u -c $WORKSPACE/output/dput.cf uploadhost $WORKSPACE/output/*$distro*.changes
done
