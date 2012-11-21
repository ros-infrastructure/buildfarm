#!/bin/env python

from rosdistro import sanitize_package_name, debianize_package_name
from stack_of_remote_repository import get_stack_of_remote_repository

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
    for name, r in sorted(repository_dict.items()):
        if 'url' not in r:
            print "'url' key missing for repository %s; skipping"%(r)
            continue
        url = r['url']
        print "downloading from %s into %s to be able to trace dependencies" % (url, workspace)
        version_number = 'release/%s/%s' % (name, r['version'])
        # try getting the release branch
        print '+++ Trying version %s' % version_number
        try:
            stack = get_stack_of_remote_repository(name, 'git', url, workspace, version_number)
        except Exception as e:
            # try getting the release branch without the debian number
            index = version_number.find('-')
            if index:
                version_number = version_number[:index]
            print '+++ Trying version %s' % version_number
            try:
                stack = get_stack_of_remote_repository(name, 'git', url, workspace, version_number)
            except Exception as e:
                # try master
                print '+++ Trying master'
                try:
                    stack = get_stack_of_remote_repository(name, 'git', url, workspace)
                except Exception as e:
                    if rosdistro == 'backports':
                        packages[name] = sanitize_package_name(name)
                        build_dependencies[name] = []
                        runtime_dependencies[name] = []
                        package_urls[name] = url
                        print "Processing backport %s, no package.xml file found in repo %s. Continuing"%(name, url)
                    else:
                        print str(e)
                    continue

        catkin_project_name = stack.name

        packages[catkin_project_name] = debianize_package_name(rosdistro, catkin_project_name)

        build_dependencies[catkin_project_name] = [d.name for d in stack.build_depends]
        runtime_dependencies[catkin_project_name] = [d.name for d in stack.depends]

        package_urls[catkin_project_name] = url

    result = {}
    urls = {}

    # combines direct buildtime- and recursive runtime-dependencies
    for k in package_urls.keys():
        #print '\nDependencies for: ', k
        build_deps = _get_dependencies(build_dependencies, k, packages)
        # recursive runtime depends of build depends
        recursive_runtime_dependencies = _get_dependencies(runtime_dependencies, k, build_deps, True)
        #print 'Recursive runtime-dependencies:', ', '.join(recursive_runtime_dependencies)
        result[packages[k]] = recursive_runtime_dependencies | build_deps
        #print 'Combined dependencies:', ', '.join(result[packages[k]])
        urls[package_urls[k]] = packages[k]
    return result, urls
