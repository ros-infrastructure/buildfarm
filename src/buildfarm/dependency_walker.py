#!/bin/env python

import vcstools
import os
import rospkg.stack
import shutil
from rosdistro import sanitize_package_name, debianize_package_name


def _get_dependencies(dependency_dict, package_name, package_list, recursive=False):
    dependencies = set(package_list[p] for p in dependency_dict[package_name] if p in package_list)
    if recursive:
        for p in  [ p for p in dependency_dict[package_name] if p in package_list ]:
            dependencies.update(_get_dependencies(dependency_dict, p, package_list, recursive))
    return dependencies

def get_dependencies(workspace, repository_list, rosdistro):
    if not os.path.isdir(workspace):
        os.makedirs(workspace)

    build_dependencies = {}
    runtime_dependencies = {}

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
                build_dependencies[name] = []
                runtime_dependencies[name] = []
                package_urls[name] = url
                print "Processing backport %s, no stack.xml file found in repo %s. Continuing"%(name, url)
            else:
                print "Warning: no stack.xml found in repository %s at %s; skipping"%(name, url)
            continue

        stack = rospkg.stack.parse_stack_file(stack_xml_path)
        catkin_project_name = stack.name

        packages[catkin_project_name] = debianize_package_name(rosdistro, catkin_project_name)

        build_dependencies[catkin_project_name] = [d.name for d in stack.build_depends]
        runtime_dependencies[catkin_project_name] = [d.name for d in stack.depends]

        package_urls[catkin_project_name] = url

    result = {}
    urls = {}

    # combines direct buildtime- and recursive runtime-dependencies
    for k in package_urls.keys():
        print '\nDependencies for: ', k
        result[packages[k]] = _get_dependencies(build_dependencies, k, packages)
        print 'Direct build-dependencies:', ', '.join(result[packages[k]])
        recursive_runtime_dependencies = _get_dependencies(runtime_dependencies, k, packages, True)
        print 'Recursive runtime-dependencies:', ', '.join(recursive_runtime_dependencies)
        result[packages[k]].update(recursive_runtime_dependencies)
        print 'Combined dependencies:', ', '.join(result[packages[k]])
        urls[package_urls[k]] = packages[k]
    return result, urls
