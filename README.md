server.yaml
===========

To use this it will look for server.yaml in $ROS_HOME/buildfarm for credentials.  Put your Jenkins login in this file.

 * url: http://jenkins.willowgarage.com:8080
 * username: USERNAME
 * password: PASSWORD

Reconfiguring Jenkins
=====================

To reconfigure Jenkins run the create_release_jobs.py script.

If you do not specify a custom workspace the gbp repositories will be cached under /tmp/repo-workspace-ROSDISTRO, so that you only have to update not clone the whole repo every time.

    scripts/create_release_jobs.py groovy --commit

If a package has been renamed or removed use the --delete option to remove jobs other than the ones just configured.

Triggering new builds
=====================

Once you have made a new release into a gbp repo, and updated the version number in the rosdistro.yaml file.  Run trigger_missing.py

    scripts/trigger_missing.py --sourcedeb-only groovy --commit

To retrigger all job generating Debian packages where the package does not yet exist run:

    scripts/trigger_missing.py groovy --commit


Load Averages
=============

Indigo
![Indigo Load](http://jenkins.ros.org/label/indigo_debbuild/loadStatistics/graph?type=sec10&width=800&height=200 "indigo_debbuild") ![Indigo Load](http://jenkins.ros.org/label/indigo_debbuild/loadStatistics/graph?type=min&width=800&height=200 "indigo_debbuild") ![Indigo Load](http://jenkins.ros.org/label/indigo_debbuild/loadStatistics/graph?type=hour&width=800&height=200 "indigo_debbuild") 
