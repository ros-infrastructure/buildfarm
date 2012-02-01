#!/bin/env python

import vcstools
import os
import yaml
import shutil


def sanitize_package_name(name):
    return name.replace('_', '-')


def get_dependencies(workspace, repository_list, rosdistro):
    if not os.path.isdir(workspace):
        os.makedirs(workspace)

    dependencies = {}

    packages = {}
    package_urls = {}


    print repository_list
    for r in repository_list:
        url = r['url']
        name = url.split('/')[-1][:-4]
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
            catkin_project_name = stack_contents['Catkin-ProjectName']

            print "Dependencies:", stack_contents['Depends']
            if 'Package' in stack_contents: # todo copied from catking-generate-debian it should be syncronized better
                packages[catkin_project_name] = stack_contents['Package']
            else:
                packages[catkin_project_name] = sanitize_package_name("ros-%s-%s"%(rosdistro, catkin_project_name))


            if 'Depends' in stack_contents:
                dependencies[catkin_project_name] = stack_contents['Depends'].split(', ')
            else:
                dependencies[catkin_project_name] = []

        package_urls[catkin_project_name] = url

    result = {}
    urls = {}
    for k, v in dependencies.iteritems():
        result[packages[k]] = [packages[p] for p in v if p in packages]
        urls[package_urls[k]] = packages[k]
    return result, urls
