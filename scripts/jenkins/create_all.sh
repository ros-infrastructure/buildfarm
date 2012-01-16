#!/bin/sh -x

if [ ! -e ./create_debjobs.py ] ; then
    echo "Run this script in same dir as create_debjobs.py"
    exit 1
fi

# wget -r http://50.28.27.175/repos/building/pool/main -A dsc -nd --directory-prefix=export

for repo in \
    catkin genmsg \
    genpy gencpp gentypelibxml genpybindings \
    roscpp_core std_msgs common_msgs \
    flann opencv2 eigen pcl
do
    ./create_debjobs.py fuerte git://github.com/wg-debs/${repo}.git \
        --dscs export --commit --username $1 --password $2
done
