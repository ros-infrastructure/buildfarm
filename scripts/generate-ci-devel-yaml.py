#!/usr/bin/env python

# Copyright (c) 2012, Willow Garage, Inc.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Willow Garage, Inc. nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" # AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import argparse
import os
import rospkg.stack
import subprocess
import sys
import urllib
import yaml

from buildfarm.stack_of_remote_repository import get_stack_of_remote_repository

def generate_ci_devel_yaml(yaml_filename, workspace=None):
    y = yaml.load(open(yaml_filename))
    #print y
    #for k in y.keys():
    #    print k
    source_repos = []
    release_repos = y['gbp-repos']
    #print release_repos
    for release_repo in release_repos:
        name = release_repo['name']
        url = release_repo['url']
        prefix = 'git://github.com/'
        suffix = '.git'
        if not url.startswith(prefix) or not url.endswith(suffix):
            sys.stderr.write('skipping unknown repository (%s, %s)\n' % (name, url))
            continue
        new_prefix = 'https://raw.github.com/'
        base_url = new_prefix + url[len(prefix):-len(suffix)]
        upstream, upstream_type = _get_upstream_info(base_url)
        #print upstream, upstream_type
        if upstream is None or upstream_type is None:
            sys.stderr.write('reading upstream info failed (%s, %s)\n' % (name, base_url))
            continue

        #print upstream, upstream_type
        if not upstream_type in ['git', 'hg', 'svn']:
            sys.stderr.write('skipping unknown repository type "%s" (%s, %s)\n' % (upstream_type, name, url))
            continue

        # fetch stack.xml from source repo
        try:
            stack = get_stack_of_remote_repository(name, upstream_type, upstream, workspace)
        except IOError:
            sys.stderr.write('skipping repository "%s" without stack.xml (%s)\n' % (name, url))
            continue
        except rospkg.stack.InvalidStack, e:
            sys.stderr.write('skipping repository "%s" with invalid stack.xml (%s): %s\n' % (name, url, str(e)))
            continue

        maintainer_email = ' '.join([m.email for m in stack.maintainers])
        stack_build_depends = [d.name for d in stack.build_depends]
        source_repo = {
            'type': 'catkin',
            'name': stack.name,
            'email': maintainer_email,
            'label': 'devel',
            'params': {
                'stack-build-depends': stack_build_depends,
                'profiles': ['devel'], # legacy stuff required by rospkg.distro
            }
        }
        upstream_type_data = {
            'distro-tag': 'distro', # legacy stuff required by rospkg.distro
            'release-tag': 'x.y.z', # legacy stuff required by rospkg.distro
        }
        if upstream_type == 'git' or upstream_type == 'hg':
            upstream_type_data['uri'] = upstream
            if upstream_type == 'git':
                upstream_type_data['dev-branch'] = 'master'
            elif upstream_type == 'hg':
                upstream_type_data['dev-branch'] = 'default'
        elif upstream_type == 'svn':
            upstream_type_data['dev'] = upstream
        source_repo['vcs_config'] = {upstream_type: upstream_type_data}

        sys.stderr.write(str(source_repo) + '\n')
        source_repos.append(source_repo)
        #if len(source_repos) == 3:
        #    break
    sys.stderr.write('\n')
    print yaml.safe_dump(source_repos, default_flow_style=False)

def _get_upstream_info(base_url):
    upstream = None
    upstream_type = None
    suffixes = {'/bloom/bloom.conf': 'bloom', '/catkin/catkin.conf': 'catkin'}
    for suffix, group in suffixes.items():
        url = base_url + suffix
        #print url
        try:
            conf_filename, _ = urllib.urlretrieve(url)
            #print conf_filename
            #print file(conf_filename).read()
        except IOError:
            sys.stderr.write('could not fetch %s (%s)\n' % (suffix, base_url))
            continue
        try:
            upstream = _get_upstream_info_field(conf_filename, '%s.upstream' % group)
            upstream_type = _get_upstream_info_field(conf_filename, '%s.upstreamtype' % group)
            break
        except KeyError:
            continue
    return upstream, upstream_type

def _get_upstream_info_field(filename, field):
    command = ['/usr/bin/git', 'config', '-f', filename, field]
    try:
        value = subprocess.check_output(command, stderr=subprocess.STDOUT)
        #print field + ' = ' + value
    except subprocess.CalledProcessError, e:
        raise KeyError('field "%s" not found' % field)
    return value.strip()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
             description='Generate CI-devel yaml from distro.yaml.')
    parser.add_argument(dest='yaml',
           help='The distro yaml file to convert')
    parser.add_argument('--repo-workspace', dest='workspace', action='store',
           help='A directory into which all the repositories will be checked out into.')
    args = parser.parse_args()

    if not args.yaml:
        sys.stderr.write('Usage: generate-ci-devel-yaml <yaml-file>\n')
        try:
            sys.exit(os.EX_USAGE)
        except AttributeError:
            sys.exit(1)

    filename = args.yaml
    if not os.path.isfile(filename):
       sys.stderr.write('file "%s" not found\n')
       sys.exit(1)

    generate_ci_devel_yaml(filename, args.workspace)
