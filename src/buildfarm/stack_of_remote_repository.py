#!/usr/bin/env python

from __future__ import print_function
import os
import rospkg.stack
import shutil
import tempfile
import vcstools

def get_stack_of_remote_repository(name, type, url, workspace=None, version=None):
    if workspace is None:
        workspace = tempfile.mkdtemp()
    if not os.path.isdir(workspace):
        os.makedirs(workspace)

    #print('Working on repository "%s" at "%s"...' % (name, url))

    # fetch repository
    workdir = os.path.join(workspace, name)
    client = vcstools.VcsClient(type, workdir)
    is_good = False
    if client.path_exists():
        if client.get_url() == url:
            is_good = client.update(version if version is not None else '')
        else:
            shutil.rmtree(workdir)
            is_good = client.checkout(url, version=version if version is not None else '', shallow=True)
    else:
        is_good = client.checkout(url, version=version if version is not None else '', shallow=True)

    if not is_good:
        raise RuntimeError('Impossible to update/checkout repo')

    # parse stack.xml
    stack_xml_path = os.path.join(workdir, 'stack.xml')
    if not os.path.isfile(stack_xml_path):
        raise IOError('No stack.xml found in repository "%s" at "%s"; skipping' % (name, url))

    return rospkg.stack.parse_stack_file(stack_xml_path)
