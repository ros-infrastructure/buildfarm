#!/bin/env python

from __future__ import print_function

import os
import rospkg.stack
import shutil
import tempfile
import vcstools

from rosdistro import sanitize_package_name, debianize_package_name


def get_stack_of_remote_repository(name, type_, url, workspace=None, version=None, skip_update=False):
    if workspace is None:
        workspace = tempfile.mkdtemp()
    if not os.path.isdir(workspace):
        os.makedirs(workspace)

    # fetch repository
    workdir = os.path.join(workspace, name)
    client = vcstools.VcsClient(type_, workdir)
    is_good = False
    if client.path_exists():
        if client.get_url() == url:
            if not skip_update:
                is_good = client.update(version if version is not None else '')
            else:
                is_good = True
        if not is_good:
            shutil.rmtree(workdir)
    if not is_good:
        is_good = client.checkout(url, version=version if version is not None else '')

    if not is_good:
        raise RuntimeError('Impossible to update/checkout repo.')

    # parse stack.xml
    stack_xml_path = os.path.join(workdir, 'stack.xml')
    if not os.path.isfile(stack_xml_path):
        raise IOError('No stack.xml found in repository.')

    return rospkg.stack.parse_stack_file(stack_xml_path)


def get_stacks(workspace, repository_dict, rosdistro, skip_update=False):
    stacks = {}

    #print repository_dict
    errors = []
    for name, r in sorted(repository_dict.items()):
        url = r.url
        if r.full_version is None:
            print("Ignoring '%s' from '%s' since version is None." % (name, url))
            continue
        version_number = 'release/%s/%s' % (name, r.full_version)
        print("Get '%s' from '%s' from tag '%s'" % (name, url, version_number))
        # try getting the release branch
        stack = None
        try:
            stack = get_stack_of_remote_repository(name, 'git', url, workspace, version_number, skip_update)
        except Exception as e:
            # try getting the release branch without the debian number if it has one
            index = version_number.rfind('-')
            if index == -1:
                print("Could not fetch '%s' from '%s' with version '%s': %s" % (name, url, version_number, e))
                errors.append(name)
                continue
            version_number = version_number[:index]
            print("  trying tag '%s'" % version_number)
            try:
                stack = get_stack_of_remote_repository(name, 'git', url, workspace, version_number, skip_update)
            except Exception as e:
                print("Could not fetch '%s' from '%s' with version '%s': %s" % (name, url, version_number, e))
                try:
                    # Support for the bloom 0.3 tag locations.  
                    version_number = 'release/%s/%s/%s' % (rosdistro, name, r.full_version)
                    stack = get_stack_of_remote_repository(name, 'git', url, workspace, version_number, skip_update)
                except Exception as e:
                    print("Could not fetch '%s' from '%s' with version '%s': %s" % (name, url, version_number, e))
                    errors.append(name)
                    continue

        if stack:
            stacks[name] = stack
        elif rosdistro == 'backports':
            stack[name] = None
            print("Processing backport %s, no package.xml file found in repo %s. Continuing" % (name, url))

    if errors:
        raise RuntimeError('Could not fetch stacks: %s' % ', '.join(errors))

    return stacks


def _get_dependencies(dependency_dict, package_name, package_list, recursive=False):
    dependencies = set(package_list[p] for p in dependency_dict[package_name] if p in package_list)
    if recursive:
        for p in [p for p in dependency_dict[package_name] if p in package_list]:
            dependencies.update(_get_dependencies(dependency_dict, p, package_list, recursive))
    return dependencies


def get_dependencies(rosdistro, stacks):
    packages = {}
    build_dependencies = {}
    runtime_dependencies = {}

    for name in sorted(stacks.keys()):
        stack = stacks[name]

        if stack is None:
            packages[name] = sanitize_package_name(name)
            build_dependencies[name] = []
            runtime_dependencies[name] = []
        else:
            catkin_project_name = stack.name
            packages[catkin_project_name] = debianize_package_name(rosdistro, catkin_project_name)
            build_dependencies[catkin_project_name] = [d.name for d in stack.build_depends]
            runtime_dependencies[catkin_project_name] = [d.name for d in stack.depends]

    result = {}
    # combines direct buildtime- and recursive runtime-dependencies
    for k in packages.keys():
        #print '\nDependencies for: ', k
        build_deps = _get_dependencies(build_dependencies, k, packages)
        # recursive runtime depends of build depends
        recursive_runtime_dependencies = _get_dependencies(runtime_dependencies, k, packages, True)
        #print 'Recursive runtime-dependencies:', ', '.join(recursive_runtime_dependencies)
        result[packages[k]] = build_deps | recursive_runtime_dependencies
        #print 'Combined dependencies:', ', '.join(result[packages[k]])
    return result
