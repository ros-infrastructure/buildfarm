from __future__ import print_function
import argparse
import yaml

import os
import distutils.version
import urllib2
import json
import sys

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse #py3k


#### PULLED FROM ROSDEP2 
#TODO: Delete this module.  This is a temporary experiment

GITHUB_V2_API_REPOS = 'https://github.com/api/v2/json/repos/'
PATTERN_GITHUB_V2_API_REPOS_SHOW_TAGS = GITHUB_V2_API_REPOS + 'show/%(org_name)s/%(repo_name)s/tags'
# include extra filename on the end to help brew with its infererence rules.  Github should ignore them.
PATTERN_GITHUB_TARBALL_DOWNLOAD = 'https://github.com/%(org_name)s/%(repo_name)s/tarball/%(tag_name)s/%(repo_name)s-%(version)s.tar.gz'

def get_api(api_pattern, org_name, repo_name):
    return api_pattern%locals()

def list_tags(org_name, repo_name, prefix):
    url = get_api(PATTERN_GITHUB_V2_API_REPOS_SHOW_TAGS, org_name, repo_name)
    print("getting org_name", org_name)
    print("getting URL", url)
    f = urllib2.urlopen(url)
    json_data = json.load(f)
    f.close()
    return [t for t in json_data['tags'].keys() if t.startswith(prefix)]

def get_org_name(url):
    parsed = urlparse.urlparse(url)
    org_name = os.path.dirname(parsed.path)
    if org_name.startswith('git@github.com:/'):
        org_name = org_name[len('git@github.com:/'):]
    return org_name.lstrip('/')

def get_repo_name(url):
    repo_name = os.path.basename(url)
    if repo_name.endswith('.git'):
        repo_name = repo_name[:-4]
    return repo_name

def compute_version_for_latest(project_name, org_name, repo_name, distro_name):
    """
    Compute the latest upstream tag and return a github.com download URL for that tarball
    """
    #TODO: update for h turtle
    assert distro_name in ['fuerte', 'groovy']
    if distro_name == 'fuerte':
        release = 'lucid'
    else:
        release = 'precise'
    project_name = project_name.replace('_', '-')
    prefix = 'debian/ros-%s-%s_'%(distro_name, project_name)
    suffix = '_%s'%(release)
    tags = list_tags(org_name, repo_name, prefix)
    tags = [t[:-len(suffix)] for t in tags if t.endswith(suffix)]
    if not tags:
        return None
    print("TAGS", [t[len(prefix):] for t in tags])
    
    versions = sorted([distutils.version.LooseVersion(t[len(prefix):]) for t in tags])
    if not versions:
        return None
    version = versions[-1].vstring #for pattern
    return '%s%s%s'%(prefix, version, suffix)

#### End pull

URL_PROTOTYPE="https://raw.github.com/ros/rosdistro/master/releases/%s.yaml"

def parse_options():
    parser = argparse.ArgumentParser(
             description='Create a set of jenkins jobs '
             'for source debs and binary debs for a catkin package.')
    parser.add_argument('--fqdn', dest='fqdn',
           help='The source repo to push to, fully qualified something...',
           default='50.28.27.175')
    parser.add_argument(dest='rosdistro',
           help='The ros distro. electric, fuerte, galapagos')
    parser.add_argument('--distros', nargs='+',
           help='A list of debian distros. Default: %(default)s',
           default=[])
    parser.add_argument('--commit', dest='commit',
           help='Really?', action='store_true')
    parser.add_argument('--repo-workspace', dest='repos', action='store',
           help='A directory into which all the repositories will be checked out into.')
    parser.add_argument('--username',dest='username')
    parser.add_argument('--password',dest='password')
    args = parser.parse_args()
    if args.commit and ( not args.username or not args.password ):
        print('If you are going to commit, you need a username and pass.',file=sys.stderr)
        sys.exit(1)
    return parser.parse_args()


def compute_rosinstall_snippet(local_name, gbp_url, distro_name):
    if 'github' not in gbp_url:
        print( "this script requires github urls, %s is not one"%gbp_url)
    org_name = get_org_name(gbp_url)
    repo_name = get_repo_name(gbp_url)

    version = compute_version_for_latest(local_name, org_name, repo_name, distro_name)
    if version is None:
        return None
    config = {}
    config['local-name'] = local_name

    config['version'] = version
    #config['version'] = '%s-%s'%(local_name, version)
    config['uri'] = gbp_url
    return {'git': config}

import time

def timed_compute_rosinstall_snippet(local_name, gbp_url, distro_name):
    time.sleep(1.0)
    return compute_rosinstall_snippet(local_name, gbp_url, distro_name)

if __name__ == "__main__":
    args = parse_options()

    print("Fetching " + URL_PROTOTYPE%args.rosdistro)
    repo_map = yaml.load(urllib2.urlopen(URL_PROTOTYPE%args.rosdistro))
    if 'release-name' not in repo_map:
        print("No 'release-name' key in yaml file")
        sys.exit(1)
    if repo_map['release-name'] != args.rosdistro:
        print('release-name mismatch (%s != %s)'%(repo_map['release-name'],args.rosdistro))
        sys.exit(1)
    if 'gbp-repos' not in repo_map:
        print("No 'gbp-repos' key in yaml file")
        sys.exit(1)

    rosinstall_data = [timed_compute_rosinstall_snippet(r['name'], r['url'], args.rosdistro) for r in repo_map['gbp-repos'] if 'url' in r and 'name' in r]
    rosinstall_data = [x for x in rosinstall_data if x]
    print(yaml.safe_dump(rosinstall_data, default_flow_style=False))
