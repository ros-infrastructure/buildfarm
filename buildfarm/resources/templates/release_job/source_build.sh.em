#!/bin/bash
export ROSDISTRO_INDEX_URL=@(ROSDISTRO_INDEX_URL)
RELEASE_URI=@(RELEASE_URI)
FQDN=@(FQDN)
PACKAGE=@(PACKAGE)
ROSDISTRO=@(ROSDISTRO)
SHORT_PACKAGE_NAME=@(SHORT_PACKAGE_NAME)


cd $WORKSPACE/monitored_vcs
. setup.sh


# Verify a clean workspace and output directory
rm -rf $WORKSPACE/output
rm -rf $WORKSPACE/workspace

$WORKSPACE/monitored_vcs/scripts/generate_sourcedeb $RELEASE_URI $PACKAGE $ROSDISTRO $SHORT_PACKAGE_NAME --working $WORKSPACE/workspace --output $WORKSPACE/output --repo-fqdn $FQDN 

# clean up the workspace to save disk space
rm -rf $WORKSPACE/workspace