#!/usr/bin/env python

from __future__ import print_function
import argparse
import shutil
import sys
import tempfile
import urllib2
import yaml


from buildfarm import dependency_walker, release_jobs

import rospkg.distro

from buildfarm.rosdistro import debianize_package_name

#import pprint # for debugging only, remove

URL_PROTOTYPE = 'https://raw.github.com/ros/rosdistro/master/releases/%s.yaml'

BUILD_JOB_LINK_URL = 'http://jenkins.willowgarage.com:8080/job/%s_binarydeb_%s_%s/'


def parse_options():
    parser = argparse.ArgumentParser(
             description='Render critical dependencies.')
    parser.add_argument('--fqdn', dest='fqdn',
           help='The source repo to push to, fully qualified something...',
           default='50.28.27.175')
    parser.add_argument(dest='rosdistro',
           help='The ros distro. electric, fuerte, groovy')
    parser.add_argument('--distros', nargs='+',
           help='A list of debian distros. Default: %(default)s',
           default=[])
    parser.add_argument('--commit', dest='commit',
           help='Really?', action='store_true', default=False)
    parser.add_argument('--repo-workspace', dest='repos', action='store',
           help='A directory into which all the repositories will be checked out into.')
    return parser.parse_args()

def display_missing_table(missing):
    strout = ''
    missing_names = sorted(missing.keys())
    for s in missing_names:
        distarches = missing[s]
        strout += "package %s missing versions: %s\n" % (s, distarches)

    return strout
               

class BlockingAnalysis(object):
    def __init__(self, missing, jobgraph, distro, arch):
        self.distro = distro
        self.arch = arch
        self.distarch = '%s_%s' % (distro, arch)
        self.missing_list = [m for m, v in missing.iteritems() if self.distarch in v]
        self.jobgraph = jobgraph
        self.__cache = {}

    def display_blocking(self):

        outstr = ''
        for s in self.missing_list:
            #print ("Missing stack %s being analyized" % s)
            outstr += "Missing stack %s blocked by:\n" % s
            outstr += self.display_blocking_specific(s)
        return outstr

    def display_blocking_specific(self, stack):
        if stack in self.__cache:
            return self.__cache[stack]
        
        outstr = ''
        #print("blocking analysis of %s" % stack)
        if stack in self.missing_list:
            outstr += "%s" % stack
            if not stack in self.jobgraph:
                print ("Error %s not in jobgraph" % stack)
                return ''
            #print ("looking at children %s" % self.jobgraph[stack])
            counter = 0
            for d in self.jobgraph[stack]:
                if d not in self.missing_list:
                    #print ("dependency %s present, skipping" % d)
                    continue
                if counter == 0:
                    outstr += '\n'
                counter += 1
                childstr = self.display_blocking_specific(d)
                lines = ['    %s\n'% l for l in childstr.splitlines()]
                for l in lines:
                    outstr += l
            if counter == 0:
                outstr += ' ***Blocking***\n'
        else:
            print ("stack %s not missing for %s" % (stack, self.distarch))
        self.__cache[stack] = outstr
        return outstr

    def compute_critical_packages(self):
        reverse_deps = {}
        critical_package_list = []
        for m in self.missing_list:
            missing_depends = [d for d in self.jobgraph[m] if d in self.missing_list]
            if not missing_depends:
                critical_package_list.append(m)
            for d in missing_depends:
                if d in reverse_deps:
                    reverse_deps[d].add(m)
                else:
                    reverse_deps[d] = set([m])
                

        critical_packages = {}
        for p in critical_package_list:
            if p in reverse_deps:
                critical_packages[p] = reverse_deps[p]
            else:
                critical_packages[p] = set()
        return critical_packages

        

    def display_critical_packages(self):
        outstr = ''
        for p, deps in sorted(self.compute_critical_packages().iteritems()):
            
            outstr += "package %s is blocking: " % p
            if deps:
                outstr += BUILD_JOB_LINK_URL % (p, self.distro, self.arch) + "\n"
            else:
                outstr += "None\n"
                
            
            for d in sorted(deps):
                outstr += "    %s\n" % d

        return outstr


def debianize_missing(missing):

    debianized_missing = {}
    for s, v in missing.iteritems():
        debianized_missing[debianize_package_name(args.rosdistro, s)] = v
    return debianized_missing



if __name__ == '__main__':
    args = parse_options()
    repo = 'http://%s/repos/building' % args.fqdn

    print('Fetching "%s"' % (URL_PROTOTYPE % args.rosdistro))
    repo_map = yaml.load(urllib2.urlopen(URL_PROTOTYPE % args.rosdistro))
    if 'release-name' not in repo_map:
        print('No "release-name" key in yaml file')
        sys.exit(1)
    if repo_map['release-name'] != args.rosdistro:
        print('release-name mismatch (%s != %s)' % (repo_map['release-name'], args.rosdistro))
        sys.exit(1)
    if 'repositories' not in repo_map:
        print('No "repositories" key in yaml file')
    if 'type' not in repo_map or repo_map['type'] != 'gbp':
        print('Wrong type value in yaml file')
        sys.exit(1)

    workspace = args.repos
    try:
        if not args.repos:
            workspace = tempfile.mkdtemp()
        (dependencies, package_names_by_url) = dependency_walker.get_dependencies(workspace, repo_map['repositories'], args.rosdistro)
        dry_jobgraph = release_jobs.dry_generate_jobgraph(args.rosdistro) 
        
        combined_jobgraph = {}
        for k, v in dependencies.iteritems():
            combined_jobgraph[k] = v
        for k, v in dry_jobgraph.iteritems():
            combined_jobgraph[k] = v

        # setup a job triggered by all other debjobs 
        combined_jobgraph[debianize_package_name(args.rosdistro, 'metapackages')] = combined_jobgraph.keys()

    finally:
        if not args.repos:
            shutil.rmtree(workspace)

    missing = release_jobs.compute_missing(
        args.distros,
        args.fqdn,
        rosdistro=args.rosdistro)

    #print (display_missing_table(missing))


    debianized_missing = debianize_missing(missing)



    ba = BlockingAnalysis(debianized_missing, combined_jobgraph, 'precise', 'amd64')
    #print ("Blocking analysis output:", ba.display_blocking())

    print ("critical packages are:")
    print (ba.display_critical_packages())
