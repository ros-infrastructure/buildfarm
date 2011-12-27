(mkdir export && cd export && wget -qr http://50.28.27.175/repos/building/pool/main -A dsc -nd )

for repo in \
    catkin genmsg \
    genpy gencpp gentypelibxml genpybindings \
    roscpp_core std_msgs \
do
    ./create_debjobs.py \
        fuerte \
        git://github.com/wg-debs/${repo}.git \
        --dscs export --commit
done
