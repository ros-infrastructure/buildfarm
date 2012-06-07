#!/bin/env python

import vcstools
import os
import rospkg.stack
import shutil


def sanitize_package_name(name):
    return name.replace('_', '-')


def get_dependencies(workspace, repository_list, rosdistro):
    if not os.path.isdir(workspace):
        os.makedirs(workspace)

    dependencies = {}

    packages = {}
    package_urls = {}

    #print repository_list
    for r in repository_list:
        if 'url' not in r or 'name' not in r:
            print "'name' and/or 'url' keys missing for repository %s; skipping"%(r)
            continue
        url = r['url']
        name = r['name']
        print "Working on repository %s at %s..."%(name, url)

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

        stack_xml_path = os.path.join(workdir, 'stack.xml')
        if not os.path.isfile(stack_xml_path):
            if rosdistro == 'backports':
                packages[name] = sanitize_package_name(name)
                dependencies[name] = []
                package_urls[name] = url
                print "Processing backport %s, no stack.xml file found in repo %s. Continuing"%(name, url)
            else:
                print "Warning: no stack.xml found in repository %s at %s; skipping"%(name, url)
            continue

        stack = rospkg.stack.parse_stack_file(stack_xml_path)
        catkin_project_name = stack.name

        print "Dependencies:", ', '.join([d.name for d in stack.build_depends])
        packages[catkin_project_name] = sanitize_package_name("ros-%s-%s"%(rosdistro, catkin_project_name))

        dependencies[catkin_project_name] = [d.name for d in stack.build_depends]

        package_urls[catkin_project_name] = url

    result = {}
    urls = {}
    for k, v in dependencies.iteritems():
        result[packages[k]] = [packages[p] for p in v if p in packages]
        urls[package_urls[k]] = packages[k]
    return result, urls
