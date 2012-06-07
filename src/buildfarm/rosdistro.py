#!/usr/bin/env python


from __future__ import print_function

import yaml, urllib2

URL_PROTOTYPE="https://raw.github.com/ros/rosdistro/master/releases/%s.yaml"


# todo raise not exit
class Rosdistro:
    def __init__(self, rosdistro_name):
        self._rosdistro = rosdistro_name
        self._targets = None
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
            if 'name' in n.keys() and 'version' in n.keys():
                self._repoinfo[n['name']] = n['version']

    def get_version(self, stack_name):
        if stack_name in self._repoinfo.keys():
            return self._repoinfo[stack_name]
        else:
            return None

    def get_target_distros(self):
        if self._targets is None: # Different than empty list
            self._targets = get_target_distros(self._rosdistro)
        return self._targets

    def get_default_target(self):
        if self._targets is None:
            self.get_target_distros()
        if len(self._targets) == 0:
            print("Warning no targets defined for distro %s"%self._rosdistro)
            return None
        return self._targets[0]

    def get_stack_rosinstall_snippet(self, distro = None):
        if not distro:
            distro = self.get_default_target()
            

    def compute_rosinstall_snippet(self, local_name, gbp_url, version, distro_name):

        if version is None:
            print ("Error version unset for %s"%local_name)
            return None
        config = {}
        config['local-name'] = local_name

        config['version'] = 'upstream/%s'%version
        config['version'] = 'debian/ros-%s-%s_%s_%s'%(self._rosdistro, local_name, version, distro_name)
        #config['version'] = '%s-%s'%(local_name, version)
        config['uri'] = gbp_url
        return {'git': config}


    def compute_rosinstall_distro(self, rosdistro, distro_name):
        rosinstall_data = [self.compute_rosinstall_snippet(r['name'], r['url'], r['version'], rosdistro) for r in self.repo_map['gbp-repos'] if 'url' in r and 'name' in r and 'version' in r]
        return rosinstall_data
        


def get_target_distros(rosdistro):
    print("Fetching " + URL_PROTOTYPE%'targets')
    targets_map = yaml.load(urllib2.urlopen(URL_PROTOTYPE%'targets'))
    my_targets = [x for x in targets_map if rosdistro in x]
    if len(my_targets) != 1:
        print("Must have exactly one entry for rosdistro %s in targets.yaml"%(rosdistro))
        sys.exit(1)
    return my_targets[0][rosdistro]
