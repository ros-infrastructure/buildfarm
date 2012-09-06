#!/usr/bin/env python

from __future__ import print_function
import argparse
import shutil
import sys
import tempfile
import urllib2
import yaml

import pprint

from buildfarm import dependency_walker, jenkins_support, release_jobs

import rospkg.distro

from buildfarm.rosdistro import debianize_package_name

import buildfarm.repo


URL_PROTOTYPE = 'https://raw.github.com/ros/rosdistro/master/releases/%s.yaml'


def parse_options():
    parser = argparse.ArgumentParser(
             description='Create a set of jenkins jobs '
             'for source debs and binary debs for a catkin package.')
    parser.add_argument('--fqdn', dest='fqdn',
           help='The source repo to push to, fully qualified something...',
           default='50.28.27.175')
    parser.add_argument(dest='rosdistro',
           help='The ros distro. electric, fuerte, groovy')
    parser.add_argument('--distros', nargs='+',
           help='A list of debian distros. Default: %(default)s',
           default=[])
    parser.add_argument('--commit', dest='commit',
           help='Really?', action='store_true')
    return parser.parse_args()


def compute_missing(distros, fqdn, rosdistro):

    repo_url = 'http://%s/repos/building' % fqdn

    print('Fetching "%s"' % (URL_PROTOTYPE % rosdistro))
    repo_map = yaml.load(urllib2.urlopen(URL_PROTOTYPE % rosdistro))


    # What ROS distro are we configuring?
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

    # Figure out default distros.  Command-line arg takes precedence; if
    # it's not specified, then read targets.yaml.
    if distros:
        default_distros = distros
    else:
        print('Fetching "%s"' % (URL_PROTOTYPE % 'targets'))
        targets_map = yaml.load(urllib2.urlopen(URL_PROTOTYPE % 'targets'))
        my_targets = [x for x in targets_map if rosdistro in x]
        if len(my_targets) != 1:
            print('Must have exactly one entry for rosdistro "%s" in targets.yaml' % rosdistro)
            sys.exit(1)
        default_distros = my_targets[0][rosdistro]

    arches = ['amd64', 'i386']

    # We take the intersection of repo-specific targets with default
    # targets.
    missing = {}
    for short_package_name, r in repo_map['repositories'].items():
        if 'url' not in r:
            print('"url" key missing for repository "%s"; skipping' % r)
            continue
        url = r['url']
        if 'target' not in r or r['target'] == 'all':
            target_distros = default_distros
        else:
            target_distros = list(set(r['target']) & set(default_distros))

        print ('Analyzing WET stack "%s" for "%s"' % (r['url'], target_distros))
        
        # todo check if sourcedeb is present with the right version
        deb_name = debianize_package_name(rosdistro, short_package_name)
        

        missing = {}
        for d in target_distros:
            missing[deb_name] = []
            if not buildfarm.repo.deb_in_repo(repo_url, deb_name, ".*", d, arch='na', source=True):
                missing[deb_name].append('source')
            for a in arches:
                if not buildfarm.repo.deb_in_repo(repo_url, deb_name, ".*", d, a):
                    missing[deb_name].append('%s_%s' % (d, a))

                                               
        # if not trigger sourcedeb

        # else if binaries don't exist trigger them
        for d in target_distros:
            for a in arches:
                pass#missing[short_package_name] = ['source']
        


        

    #dry stacks
    # dry dependencies
    dist = rospkg.distro.load_distro(rospkg.distro.distro_uri(rosdistro))

    distro_arches = []
    for d in default_distros:
        for a in arches:
            distro_arches.append( (d, a) )

    for s in dist.stacks:
        print ("Analyzing DRY job [%s]" % s)
        missing[s] = []
        # for each distro arch check if the deb is present. If not trigger the build. 
        for (d, a) in distro_arches:
            if not buildfarm.repo.deb_in_repo(repo_url, debianize_package_name(rosdistro, s), ".*", d, a):
                missing[s].append( '%s_%s' % (d, a) )


    pp = pprint.PrettyPrinter()
    print ("net Missing")
    pp.pprint (missing)


    return missing

if __name__ == '__main__':
    args = parse_options()



    missing = compute_missing(
        args.distros,
        args.fqdn,
        rosdistro=args.rosdistro)


    if args.commit:
        jenkins_instance = jenkins_support.JenkinsConfig_to_handle(jenkins_support.load_server_config_file(jenkins_support.get_default_catkin_debs_config()))


        for s, dist_archs in missing.iteritems():
            if 'source' in dist_archs:
                job_name = '%s_sourcedeb' % (debianize_package_name(args.rosdistro, s) )
                print ("Triggering %s" % (job_name) )
                try:
                    jenkins_instance.build_job(job_name)
                except Exception, ex:
                    print ("Failed to trigger %s: %s" % (job_name, ex))
                # don't trigger binaries as the sourcedeb will trigger them anyway
                continue
    
            for da in dist_archs:
                job_name = '%s_binarydeb_%s' % (debianize_package_name(args.rosdistro, s), da )
                print ("Triggering %s" % (job_name) )
                try: 
                    jenkins_instance.build_job(job_name)
                except Exception, ex:
                    print ("Failed to trigger %s: %s" % (job_name, ex) )


    else:
        
        print('This was not pushed to the server.  If you want to do so use "--commit" to do it for real.')
