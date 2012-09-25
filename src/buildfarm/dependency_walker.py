#!/bin/env python

from rosdistro import sanitize_package_name, debianize_package_name
from stack_of_remote_repository import get_packages_of_remote_repository

def _get_dependencies(dependency_dict, package_name, package_list, recursive=False):
    dependencies = set(package_list[p] for p in dependency_dict[package_name] if p in package_list)
    if recursive:
        for p in  [ p for p in dependency_dict[package_name] if p in package_list ]:
            dependencies.update(_get_dependencies(dependency_dict, p, package_list, recursive))
    return dependencies

def get_dependencies(workspace, repository_dict, rosdistro, skip_update=False):
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
        if 'version' not in r:
            print "'version' key missing for repository %s; assuming master"%(r)
            version = 'master'
        else:
            version = r['version']

        print "downloading from %s version %s into %s to be able to trace dependencies" % (url, version, workspace)
        try:
            found_packages = get_packages_of_remote_repository(name, 'git', url, workspace, version = version, skip_update = skip_update)
        except VcsError, e:
            print "Failed checking out repo:", str(e)
            continue
        if not found_packages:
            if rosdistro == 'backports':
                packages[name] = sanitize_package_name(name)
                build_dependencies[name] = []
                runtime_dependencies[name] = []
                package_urls[name] = url
                print "Processing backport %s, no stack.xml file found in repo %s. Continuing" % (name, url)
            else:
                print "No Packages found in %s from %s" % (name, url)
            continue


        for p in found_packages.itervalues():
            
            packages[p.name] = debianize_package_name(rosdistro, p.name)

            build_dependencies[p.name] = [d.name for d in p.build_depends] + [d.name for d in p.buildtool_depends]
            runtime_dependencies[p.name] = [d.name for d in p.run_depends]

            package_urls[p.name] = url


    print "build_dependencies", build_dependencies
    print "runtime_dependencies", runtime_dependencies

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
