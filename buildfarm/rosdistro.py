#!/usr/bin/env python


from __future__ import print_function

import sys
import yaml, urllib2

URL_PROTOTYPE="https://raw.github.com/ros/rosdistro/master/releases/%s.yaml"

class RepoMetadata(object):
    def __init__(self, name, url, version, status = None):
        self.name = name
        self.url = url
        self.version = version
        self.status = status


def sanitize_package_name(name):
    return name.replace('_', '-')


def debianize_package_name(rosdistro, name):
    return sanitize_package_name("ros-%s-%s"%(rosdistro, name))


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
        if 'repositories' not in self.repo_map:
            print("No 'repositories' key in yaml file")
            sys.exit(1)
        self._repoinfo = {}
        self._package_in_repo = {}
        for name, n in self.repo_map['repositories'].items():
            if 'url' in n.keys() and 'version' in n.keys():
                self._repoinfo[name] = RepoMetadata(name, n['url'], n['version'])
                if 'packages' in n.keys():
                    self._repoinfo[name].packages = n['packages']
                    for p in n['packages']:
                        self._package_in_repo[p] = name
                else:
                    print("Missing required 'packages' for %s.  Assuming this is a unary stack" % name)
                    self._repoinfo[name].packages = {name: None}
                    self._package_in_repo[name] = name
            else:
                print("Missing required 'url' or 'version' for %s" % name)

    def debianize_package_name(self, package_name):
        return debianize_package_name(self._rosdistro, package_name)

    def get_repo_list(self):
        return self._repoinfo.iterkeys()

    def get_repos(self):
        return self._repoinfo.itervalues()

    def get_package_list(self):
        return self._repoinfo.iterkeys()
                
    def get_version(self, package_name):
        if package_name in self._package_in_repo:
            return self._repoinfo[self._package_in_repo[package_name]].version
        else:
            return None

    def get_status(self, stack_name):
        if stack_name in self._repoinfo.keys():
            return self._repoinfo[stack_name].status
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
        rosinstall_data = [self.compute_rosinstall_snippet(name, r['url'], r['version'], rosdistro) for name, r in self.repo_map['repositories'].items() if 'url' in r and 'version' in r]
        return rosinstall_data
        


def get_target_distros(rosdistro):
    print("Fetching " + URL_PROTOTYPE%'targets')
    targets_map = yaml.load(urllib2.urlopen(URL_PROTOTYPE%'targets'))
    my_targets = [x for x in targets_map if rosdistro in x]
    if len(my_targets) != 1:
        print("Must have exactly one entry for rosdistro %s in targets.yaml"%(rosdistro))
        sys.exit(1)
    return my_targets[0][rosdistro]
