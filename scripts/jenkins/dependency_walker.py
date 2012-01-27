#!/bin/env python

import vcstools
import os
import yaml
import shutil

def get_dependencies(workspace, repository_list):
    if not os.path.isdir(workspace):
        os.makedirs(workspace)

    dependencies = {}
    packages = set()

    print repository_list
    for r in repository_list:
        url = r['url']
        name = url.split('/')[-1][:-4]
        packages.add(name)
        print name, url
        workdir = os.path.join(workspace, name)
        client = vcstools.VcsClient('git', workdir)
        if client.path_exists():
            if client.get_url() == url:
                client.update("")
            else:
                shutil.rmtree(workdir)
                client.checkout(url)
        else:
            client.checkout(url)

        with open(os.path.join(workdir, 'stack.yaml'), 'r') as f:
            stack_contents = yaml.load(f.read())
            print "Dependencies:", stack_contents['Depends']
            dependencies[name] = stack_contents['Depends'].split(', ')



    result = {}
    for k, v in dependencies.iteritems():
        result['ros-fuerte-%s'%k] = ["ros-fuerte-%s"%p for p in v if p in packages]
    return result

#def invert_dependencies(dependencies_map):
#    dependents = set()
#    for k, v in dependencies_map.iteritems():
#        dependents.add(k)
#        dependents.update(v)
