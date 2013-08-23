#!/usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2009, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
Build debs for a package and all of its dependencies as necessary
"""

import os
import sys
import cStringIO
import subprocess
import shutil
import tempfile
import yaml
import urllib
import urllib2
import stat
import tempfile
import time
import rospkg.distro

from core import debianize_name, debianize_version
from repo import deb_in_repo, load_Packages, get_repo_version, get_stack_version, BadRepo

NAME = 'list_missing.py' 
TARBALL_URL = "https://code.ros.org/svn/release/download/stacks/%(stack_name)s/%(base_name)s/%(f_name)s"

REPO_URL="http://packages.ros.org/%(repo)s/"
SHADOW_REPO=REPO_URL%{'repo': 'ros-shadow'}
SHADOW_FIXED_REPO=REPO_URL%{'repo': 'ros-shadow-fixed'}
ROS_REPO=REPO_URL%{'repo': 'ros'}

HUDSON='http://build.willowgarage.com/'

ARCHES = ['i386', 'amd64'] #,'armel'

import traceback

_distro_yaml_cache = {}

def svn_url_exists(url):
    """
    @return: True if SVN url points to an existing resource
    """
    fh = urllib.urlopen(url)
    if fh.getcode() == 200:
        return True
    return False

def load_info(stack_name, stack_version):
    
    base_name = "%s-%s"%(stack_name, stack_version)
    f_name = base_name + '.yaml'

    url = TARBALL_URL%locals()

    try:
        if url in _distro_yaml_cache:
            return _distro_yaml_cache[url]
        else:
            _distro_yaml_cache[url] = l = yaml.load(urllib2.urlopen(url))
            return l
    except:
        raise Exception("Problem fetching yaml info for %s %s (%s)"%(stack_name, stack_version, url))

class MissingDefinition(Exception): pass

def compute_deps(distro, stack_name, ignore_catkinized = True):
    # for suppressing repeated error messages
    ignored = []

    seen = set()
    ordered_deps = []

    def add_stack(s):
        if s in seen:
            return
        if s not in distro.stacks:
            raise MissingDefinition("[%s] not found in distro."%(s))
        seen.add(s)
        v = distro.stacks[s].version
        try:
            si = load_info(s, v)
        except Exception as e:
            sys.stderr.write(str(e) + '\n')
            return

        for d in si['depends']:
            try:
                add_stack(d)
            except MissingDefinition as e:
                if not d in ignored:
                    sys.stderr.write("[%s] ignoring dependency [%s], possible catkin-ized\n"%(s, d))
                    ignored.append(d)
                #raise MissingDefinition("[%s] failure loading dependency [%s]: %s\n"%(s, d, e))
            except Exception as e:
                # this is a soft-fail. If the load_info fails, it means
                # the stack is missing. We will detect it missing
                # elsewhere.
                sys.stderr.write(str(e)+'\n')
        ordered_deps.append((s,v))

    if stack_name == 'ALL':
        for s in distro.released_stacks.keys():
            add_stack(s)
    else:
        add_stack(stack_name)

    if not ignore_catkinized:
        ordered_deps += [(sn, 'possibly_catkinized') for sn in ignored]

    return ordered_deps


class ExclusionList(object):
    def __init__(self, uri, distro_name, os_platform, arch):
        try:
            self.excludes = yaml.load(urllib2.urlopen(uri).read()) or {}
        except urllib2.HTTPError:
            self.excludes = {}
        self.key = "%s-%s"%(os_platform,arch)

    def check(self, stack):
        return stack in self.excludes and self.key in self.excludes[stack]


def compute_missing_depends(stack_name, distro, os_platform, arch, repo=SHADOW_REPO, lock_version=True):
    missing_deps = set()
    deps = compute_deps(distro, stack_name, ignore_catkinized = False)
    #don't include self
    deps = set([(sn, sv) for (sn, sv) in deps if not sn == stack_name])
    for sn, sv in deps:
        deb_name = "ros-%s-%s"%(distro.release_name, debianize_name(sn))
        # see if there's a dry version
        deb_version = '[0-9.-]*-[st][0-9]+~[a-z]+' 
        if not deb_in_repo(repo, deb_name, deb_version, os_platform, arch, use_regex=True):
            # now test for wet version
            wet_deb_version = '[0-9.]*-[0-9a-z]+-[0-9]+-[0-9]+-\+0000'
            if not deb_in_repo(repo, deb_name, wet_deb_version, os_platform, arch, use_regex=True):
                missing_deps.add(deb_name)

    return missing_deps

def get_missing(distro, os_platform, arch, repo=SHADOW_REPO, lock_version=True):
    distro_name = distro.release_name
    # Load the list of exclusions
    excludes_uri = "http://ros-dry-releases.googlecode.com/svn/trunk/distros/%s.excludes"%(distro_name)
    excludes = ExclusionList(excludes_uri, distro_name, os_platform, arch)

    # Find all the deps in the distro for this stack
    deps = compute_deps(distro, 'ALL')

    # These stacks are not actually relased, so we treat them as implicitly excluded
    missing_primary = set(distro.stacks.keys()) - set(distro.released_stacks.keys())
    missing_dep = set()
    missing_excluded = set(distro.stacks.keys()) - set(distro.released_stacks.keys())
    missing_excluded_dep = set()

    # Build the deps in order
    for (sn, sv) in deps:
        if not sv:
            missing_primary.add(sn)
            continue
        deb_name = "ros-%s-%s"%(distro_name, debianize_name(sn))
        if lock_version:
            deb_version = debianize_version(sv, '\w*', os_platform)
        else:
            deb_version = '[0-9.]*-[st][0-9]+~[a-z]+'
        if not deb_in_repo(repo, deb_name, deb_version, os_platform, arch, use_regex=True):
            try:
                si = load_info(sn, sv)
                depends = set(si['depends'])
            except:
                # stack is missing, including its info
                depends = set()

            # subtract any depends that aren't in the distro b/c of catkin dry/wet line
            to_remove = [d for d in depends if not d in distro.stacks]
            for d in to_remove:
                depends.remove(d)
                
            if excludes.check(sn):
                missing_excluded.add(sn)
                missing_primary.add(sn)
            elif depends.isdisjoint(missing_primary.union(missing_dep)):
                missing_primary.add(sn)
            else:
                missing_dep.add(sn)
                if not depends.isdisjoint(missing_excluded.union(missing_excluded_dep)):
                    missing_excluded_dep.add(sn)

        else:
            pass
            #print "IN", sn
    missing_primary -= missing_excluded
    missing_dep -= missing_excluded_dep

    return missing_primary, missing_dep, missing_excluded, missing_excluded_dep

def list_missing(distro, os_platform, arch):
    distro_name = distro.release_name
    missing_primary, missing_dep, missing_excluded, missing_excluded_dep = get_missing(distro, os_platform, arch)

    print "[%s %s %s]"%(distro_name, os_platform, arch)
    if not missing_primary and not missing_dep:
        print "[ok]"
    else:
        print "\nThe following stacks are missing but have deps satisfied: (%s)"%(len(missing_primary))
        print '\n'.join([" %s"%x for x in missing_primary])
        print "\nThe following stacks are missing deps: (%s)"%(len(missing_dep))
        print '\n'.join([" %s"%x for x in missing_dep])
    if missing_excluded:
        print "\nThe following stacks are excluded: (%s)"%(len(missing_excluded))
        print '\n'.join([" %s"%x for x in missing_excluded])
    if missing_excluded_dep:
        print "\nThe following stacks have deps on excluded stacks: (%s)"%(len(missing_excluded_dep))
        print '\n'.join([" %s"%x for x in missing_excluded_dep])


    return missing_primary, missing_dep

def load_distro(distro_name):
    "Load the distro from the URL"
    return rospkg.distro.load_distro(rospkg.distro.distro_uri(distro_name))

SOURCEDEB_DIR_URI = 'https://code.ros.org/svn/release/download/stacks/%(stack_name)s/%(stack_name)s-%(stack_version)s/'
SOURCEDEB_URI = SOURCEDEB_DIR_URI+'%(deb_name)s_%(stack_version)s-0~%(os_platform)s.dsc'
    
MISSING_REPO = '*'
MISSING_SOURCEDEB = '!'
MISSING_PRIMARY = '-'
MISSING_DEP = '&lt;-'
MISSING_BROKEN = '--'
MISSING_BROKEN_DEP = '&lt;--'
MISSING_EXCLUDED = 'X'
MISSING_EXCLUDED_DEP = '&lt;X'
COLORS = {
    MISSING_REPO: 'black',
    MISSING_PRIMARY: 'blue',
    MISSING_SOURCEDEB: 'yellow',
    MISSING_DEP: 'lightblue',
    MISSING_BROKEN: 'red',
    MISSING_BROKEN_DEP: 'pink',
    MISSING_EXCLUDED: 'grey',
    MISSING_EXCLUDED_DEP: 'lightgrey',
    }

def sourcedeb_url(distro, stack_name, os_platform):
    # have to setup locals for substitution
    distro_name = distro.release_name
    stack_version = distro.stacks[stack_name].version
    deb_name = "ros-%s-%s"%(distro_name, debianize_name(stack_name))
    return SOURCEDEB_URI%locals()

def get_html_legend():
    return """<h2>Stack Debbuild Status</h2>
<h3>Legend</h3>
<ul>
<li>Missing (sourcedeb): <span style="background-color: %s;">&nbsp;%s&nbsp;</span></li>
<li>Missing (deb): <span style="background-color: %s;">&nbsp;%s&nbsp;</span></li>
<li>Depends Missing: <span style="background-color: %s;">&nbsp;%s&nbsp;</span></li>
<li>Broken (deb): <span style="background-color: %s;">&nbsp;%s&nbsp;</span></li>
<li>Depends Broken (deb): <span style="background-color: %s;">&nbsp;%s&nbsp;</span></li>
<li>Excluded: <span style="background-color: %s;">&nbsp;%s&nbsp;</span></li>
<li>Depends Excluded: <span style="background-color: %s;">&nbsp;%s&nbsp;</span></li> 
</ul>"""%(COLORS[MISSING_SOURCEDEB], MISSING_SOURCEDEB, 
          COLORS[MISSING_PRIMARY], MISSING_PRIMARY, 
          COLORS[MISSING_DEP], MISSING_DEP,
          COLORS[MISSING_BROKEN], MISSING_BROKEN, 
          COLORS[MISSING_BROKEN_DEP], MISSING_BROKEN_DEP, 
          COLORS[MISSING_EXCLUDED], MISSING_EXCLUDED, 
          COLORS[MISSING_EXCLUDED_DEP], MISSING_EXCLUDED_DEP
          )
    
def get_html_header(distro_name):
    return """<html>
<head>
<title>
%(distro_name)s: debbuild report
</title>
</head>
<script type="text/javascript" src="sortable.js"></script>
<style type="text/css">
body {
  font-family: Helvetica, Arial, Verdana, sans-serif;
  font-size: 12px;
}
.title {
  background-color: lightgrey;
  padding: 10px;
}
table {
  border: 1px solid lightgrey;
}
th {
  border: 1px solid lightgrey;
}
td {
  font-size: 12px;
  border: 1px solid lightgrey;
}
</style>
<body>
<h1><span class="title">%(distro_name)s: debbuild report</span></h1>"""%locals()
    
def get_html_table_header(h, distro_name, os_platforms, arches, counts, job):
    b = cStringIO.StringIO()
    b.write("""<strong>Click [+] to trigger a new build of the selected stack/platform</strong>")
<table cellspacing=0 border="1" class="sortable" id="stackstatustable">
   <tr>
     <th>Stack</th>""")

    params = {'STACK_NAME': 'ALL'}
    for os_platform in os_platforms:
        for arch in arches:
            url = h.build_job_url('%s-%s-%s-%s'%(job, distro_name, os_platform, arch), parameters=params)
            b.write('<th>%s-%s<a href="%s">[+]</a></th>'%(os_platform, arch, url))
    b.write('</tr>')

    b.write('<tr><td>&nbsp;</td>')
    for os_platform in os_platforms:
        for arch in arches:
            b.write('<td>%s</td>'%counts['%s-%s'%(os_platform, arch)])
    b.write('</tr>')
    
    return b.getvalue()
    
def rev_to_time(rev):
    if rev[0] == 's':
        return '%s'%(time.strftime("%b %d %H:%M:%S %Y",time.localtime(int(rev[1:]))))
    else:
        return ""

def get_html_repository_status(distro, os_platforms, arches):
    b = cStringIO.StringIO()
    b.write("""<h2>Repository Status</h2>
<table border="0" cellspacing="0">
<tr>
<th>Platform</th><th>Shadow</th><th>Shadow-Fixed</th><th>Public</th>
</tr>
""")
    for os_platform in os_platforms:
        for arch in arches:
            try:
                shadow_version = get_repo_version(SHADOW_REPO, distro, os_platform, arch)
            except BadRepo:
                shadow_version = "[no repo]"
            try:
                main_version = get_repo_version(ROS_REPO, distro, os_platform, arch)
            except BadRepo:
                main_version = "[no repo]"
            try:
                fixed_version = get_repo_version(SHADOW_FIXED_REPO, distro, os_platform, arch)
            except BadRepo:
                fixed_version = "[no repo]"
            b.write("<tr valign=top><td>%s-%s</td><td>%s<br><i>%s</i></td><td>%s<br><i>%s</i></td><td>%s<br><i>%s</i></td></tr>\n"%(os_platform, arch, shadow_version, rev_to_time(shadow_version), fixed_version, rev_to_time(fixed_version), main_version, rev_to_time(main_version)))
    b.write("</table>")
    return b.getvalue()

def sourcedeb_job_url(h, distro_name, stack, stack_version):
    params = {'STACK_NAME': stack, 'DISTRO_NAME': distro_name,'STACK_VERSION': stack_version}
    return h.build_job_url('debbuild-sourcedeb', parameters=params)                            
    

def generate_allhtml_report(output, distro_name, os_platforms):
    import hudson
    h = hudson.Hudson(HUDSON)
    distro = load_distro(distro_name)

    main_repo = {}
    arches = ARCHES
    for os_platform in os_platforms:
        for arch in arches:
            try:
                main_repo["%s-%s"%(os_platform, arch)] = load_Packages(ROS_REPO, os_platform, arch)
            except:
                main_repo["%s-%s"%(os_platform, arch)] = []

    fixed_repo = {}
    arches = ARCHES
    for os_platform in os_platforms:
        for arch in arches:
            try:
                fixed_repo["%s-%s"%(os_platform, arch)] = load_Packages(SHADOW_FIXED_REPO, os_platform, arch)
            except:
                fixed_repo["%s-%s"%(os_platform, arch)] = []

    missing_primary = None
    missing_dep = None

    counts = {}
    stacks = {}
    for stack in distro.stacks.keys():
        stacks[stack] = {}

    for os_platform in os_platforms:
        for arch in arches:
            key = "%s-%s"%(os_platform, arch)
            try:
                missing_primary, missing_dep, missing_excluded, missing_excluded_dep = get_missing(distro, os_platform, arch)
            except BadRepo:
                for s in distro.stacks.iterkeys():
                    stacks[s][key] = MISSING_REPO
                counts[key] = "!"
                continue
            
            args = get_missing(distro, os_platform, arch)
            try:
                args_fixed = get_missing(distro, os_platform, arch, repo=SHADOW_FIXED_REPO, lock_version=False)
            except BadRepo:
                for s in distro.stacks.iterkeys():
                    stacks[s][key] = MISSING_REPO
                counts[key] = "!"
                continue
            counts[key] = ','.join([str(len(x)) for x in args])
            missing_primary, missing_dep, missing_excluded, missing_excluded_dep = args
            missing_primary_fixed, missing_dep_fixed, missing_excluded_fixed, missing_excluded_dep_fixed = args_fixed
            for s in missing_primary:
                if svn_url_exists(sourcedeb_url(distro, s, os_platform)):
                    stacks[s][key] = MISSING_PRIMARY
                else:
                    stacks[s][key] = MISSING_SOURCEDEB
            for s in missing_dep:
                if svn_url_exists(sourcedeb_url(distro, s, os_platform)):
                    stacks[s][key] = MISSING_DEP
                else:
                    stacks[s][key] = MISSING_SOURCEDEB
            for s in missing_primary_fixed:
                if svn_url_exists(sourcedeb_url(distro, s, os_platform)):
                    stacks[s][key] = MISSING_BROKEN
                else:
                    stacks[s][key] = MISSING_SOURCEDEB
            for s in missing_dep_fixed:
                if svn_url_exists(sourcedeb_url(distro, s, os_platform)):
                    stacks[s][key] = MISSING_BROKEN_DEP
                else:
                    stacks[s][key] = MISSING_SOURCEDEB

            for s in missing_excluded:
                stacks[s][key] = MISSING_EXCLUDED
            for s in missing_excluded_dep:
                stacks[s][key] = MISSING_EXCLUDED_DEP
           
    with open(output, 'w') as f:
        f.write(get_html_header(distro_name))
        f.write(get_html_repository_status(distro, os_platforms, arches))
        f.write(get_html_legend())
        job = 'debbuild-build-debs'
        f.write(get_html_table_header(h, distro_name, os_platforms, arches, counts, job))
        
        stack_names = sorted(stacks.keys())
        for stack in stack_names:

            d = stacks[stack]
            shadow_version = distro.stacks[stack].version

            # generate URL
            stack_name = stack
            stack_version = shadow_version
            url = SOURCEDEB_DIR_URI%locals()
            
            # MISSING_SOURCEDEB is os/arch independent, so treat row as a whole            
            sample_key = "%s-%s"%(os_platforms[0], arches[0])
            if sample_key in d and d[sample_key] == MISSING_SOURCEDEB:
                color = COLORS[d[sample_key]]
                job_url = sourcedeb_job_url(h, distro_name, stack, shadow_version)
                f.write('<tr><td bgcolor="%s"><a href="%s">%s %s</a> <a href="%s">[+]</a></td>'%(color, url, stack, shadow_version, job_url))
            else:
                if 0:
                    f.write('<tr><td><a href="%s">%s %s</a></td>'%(url, stack, shadow_version))
                else:
                    job_url = sourcedeb_job_url(h, distro_name, stack, shadow_version)
                    # temporarily including [+] for all right now to help bringup maverick
                    f.write('<tr><td><a href="%s">%s %s</a> <a href="%s">[+]</a></td>'%(url, stack, shadow_version, job_url)) 
                
            for os_platform in os_platforms:
                for arch in arches:
                    key = "%s-%s"%(os_platform, arch)

                    # compute version in actual repo
                    version_str = ''
                    try:
                        main_match = get_stack_version(main_repo[key], distro_name, stack)
                        fixed_match = get_stack_version(fixed_repo[key], distro_name, stack)
                        if main_match != shadow_version or fixed_match != shadow_version:
                            main_match = main_match or '0'
                            fixed_match = fixed_match or '0'
                            version_str = '<em>'+str(fixed_match)+', '+str(main_match)+'</em>'
                    except Exception, e:
                        print str(e)
                    
                    if key in d:
                        val = d[key]
                        color = COLORS[val]
                        params = {'STACK_NAME': stack}
                        if val == MISSING_SOURCEDEB:
                            f.write('<td bgcolor="%s">%s %s</td>'%(color, val, version_str))
                        else:
                            url = h.build_job_url('%s-%s-%s-%s'%(job, distro_name, os_platform, arch),
                                                  parameters=params)
                            f.write('<td bgcolor="%s">%s <a href="%s">[+]</a> %s</td>'%
                                    (color, val, url, version_str))
                    else:
                        f.write('<td>&nbsp;%s </td>'%version_str)
            f.write('</tr>\n')            

        f.write('\n</table></body></html>')
        

def list_missing_main():
    
    from optparse import OptionParser
    parser = OptionParser(usage="usage: %prog <distro> <os-platform> <arch>", prog=NAME)
    parser.add_option("--all", help="run on all os/arch combos for known distro",
                      dest="all", default=False, action="store_true")
    parser.add_option("--allhtml", help="generate html report", 
                      dest="allhtml", default=False, action="store_true")
    parser.add_option("-o", help="generate html report", 
                      dest="output_file", default=None, metavar="OUTPUT")

    (options, args) = parser.parse_args()

    if not options.all and not options.allhtml:
        if len(args) != 3:
            parser.error('invalid args')
        
        distro_name, os_platform, arch = args
        list_missing(load_distro(distro_name), os_platform, arch)

    # the logic here allows both --all and --allhtml to be invoked 
    if options.all:
        if len(args) != 1:
            parser.error('invalid args: only specify <distro> when using --all')
        distro_name = args[0]
        try:
            import targets
            targets = targets.os_platform[distro_name]
        except:
            parser.error("unknown distro for --all target")

        distro = load_distro(distro_name)
        missing_primary = None
        missing_dep = None
        for os_platform in targets:
            for arch in ['amd64', 'i386']:
                list_missing(distro, os_platform, arch)
                print '-'*80
                
    if options.allhtml:

        if len(args) != 1:
            parser.error('invalid args: only specify <distro> when using --all')
        distro_name = args[0]
        try:
            import targets
            os_platforms = targets.os_platform[distro_name]
        except:
            parser.error("unknown distro for --all target")

        output = options.output_file or 'report.html'
        generate_allhtml_report(output, distro_name, os_platforms)
        
        
if __name__ == '__main__':
    list_missing_main()

