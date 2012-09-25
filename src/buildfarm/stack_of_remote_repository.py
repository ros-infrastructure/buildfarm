#!/usr/bin/env python

from __future__ import print_function
import os
import rospkg.stack
import shutil
import tempfile
import vcstools

from catkin_pkg.packages import find_packages

def get_packages_of_remote_repository(name, type, url, workspace=None, version=None, skip_update=False):
    if workspace is None:
        workspace = tempfile.mkdtemp()
    if not os.path.isdir(workspace):
        os.makedirs(workspace)

    # fetch repository
    workdir = os.path.join(workspace, name)
    client = vcstools.VcsClient(type, workdir)
    if client.path_exists():
        if client.get_url() == url:
            if not skip_update:
                print ("Getting version %s" % version)
                client.update(version if version is not None else '')
        else:
            shutil.rmtree(workdir)
            client.checkout(url, version=version if version is not None else '', shallow=True)
    else:
        client.checkout(url, version=version if version is not None else '', shallow=True)


    packages = find_packages(workdir)
    
    if not packages:
        print ("Failed to find packages in", workdir, os.listdir(workdir))
    else:
        print ("Found packages", packages)
    return packages
