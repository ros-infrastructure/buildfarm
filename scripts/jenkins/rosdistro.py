#!/usr/bin/env python

import yaml, urllib2

URL_PROTOTYPE="https://raw.github.com/ros/rosdistro/master/releases/%s.yaml"


# todo raise not exit
class Rosdistro:
    def __init__(self, rosdistro_name):
        # avaliable for backwards compatability
        self.repo_map = yaml.load(urllib2.urlopen(URL_PROTOTYPE%rosdistro_name))
        if 'release-name' not in self.repo_map:
            print("No 'release-name' key in yaml file")
            sys.exit(1)
        if self.repo_map['release-name'] != rosdistro_name:
            print('release-name mismatch (%s != %s)'%(self.repo_map['release-name'],rosdistro_name))
            sys.exit(1)
        if 'gbp-repos' not in self.repo_map:
            print("No 'gbp-repos' key in yaml file")
            sys.exit(1)
        self._repoinfo = {}
        for n in self.repo_map['gbp-repos']:
            print n
            if 'name' in n and 'version' in n:
                self._repoinfo[n['name']] = n['version']

    def get_version(self, stack_name):
        if stack_name in self._repoinfo:
            return self._repoinfo[stack_name]
        else:
            return None


def get_target_distros(rosdistro):
    print("Fetching " + URL_PROTOTYPE%'targets')
    targets_map = yaml.load(urllib2.urlopen(URL_PROTOTYPE%'targets'))
    my_targets = [x for x in targets_map if rosdistro in x]
    if len(my_targets) != 1:
        print("Must have exactly one entry for rosdistro %s in targets.yaml"%(rosdistro))
        sys.exit(1)
    return my_targets[0][rosdistro]
