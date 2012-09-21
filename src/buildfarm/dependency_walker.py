#!/bin/env python

from rosdistro import sanitize_package_name, debianize_package_name
from stack_of_remote_repository import get_packages_of_remote_repository

def _get_dependencies(dependency_dict, package_name, package_list, recursive=False):
    dependencies = set(package_list[p] for p in dependency_dict[package_name] if p in package_list)
    if recursive:
        for p in  [ p for p in dependency_dict[package_name] if p in package_list ]:
            dependencies.update(_get_dependencies(dependency_dict, p, package_list, recursive))
    return dependencies

def get_dependencies(workspace, repository_dict, rosdistro):
    build_dependencies = {}
    runtime_dependencies = {}

    packages = {}
    package_urls = {}

    #print repository_dict
    for name, r in repository_dict.items():
        if 'url' not in r:
            print "'url' key missing for repository %s; skipping"%(r)
            continue
        url = r['url']
        print "downloading from %s into %s to be able to trace dependencies" % (url, workspace)
        try:
            packages = get_packages_of_remote_repository(name, 'git', url, workspace)
        except VcsError, e:
            print "Failed checking out repo:", str(e)
            continue
        if not packages:
            if rosdistro == 'backports':
                packages[name] = sanitize_package_name(name)
                build_dependencies[name] = []
                runtime_dependencies[name] = []
                package_urls[name] = url
                print "Processing backport %s, no stack.xml file found in repo %s. Continuing" % (name, url)
            else:
                print "No Packages found in %s from %s" % (name, url)
            continue

        for p in packages:

            catkin_project_name = p.name

            packages[catkin_project_name] = debianize_package_name(rosdistro, catkin_project_name)

            build_dependencies[catkin_project_name] = [d.name for d in p.build_depends] + [d.name for d in p.buildtool_depends]
            runtime_dependencies[catkin_project_name] = [d.name for d in p.run_depends]

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
