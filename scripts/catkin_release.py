#!/usr/bin/env python

from __future__ import print_function
import os, sys, yaml, pprint, em, os.path, datetime, dateutil.tz, platform, time
import subprocess
import tarfile
from subprocess import Popen, CalledProcessError
'''
The Debian binary package file names conform to the following convention:
<foo>_<VersionNumber>-<DebianRevisionNumber>_<DebianArchitecture>.deb

PackagePrefix is a ROS mangling, ros-electric-,ros-fuerte-,ros-X- etc...
Distribution is an ubuntu distro
Version is the upstream version
DebianInc is some number that is incremental for package maintenance
Changes is a bulleted list of changes.
'''
def parse_options():
    import argparse
    parser = argparse.ArgumentParser(description='Creates/updates a gpb from a catkin project.')
    parser.add_argument(dest='repo_uri',
            help='A pushable git buildpackage repo uri.')
    parser.add_argument('--working', help='A scratch build path. Default: %(default)s', default='/tmp/catkin_gbp')
    parser.add_argument(dest='upstream',
            help='The location of your sources to create an upstream snap shot from.')
    parser.add_argument(dest='rosdistro', help='The ros distro. electric, fuerte, galapagos')
    parser.add_argument('--output', help='The result of source deb building will go here. For debuging purposes. Default: %(default)s', default='/tmp/catkin_debs')
    parser.add_argument('--distros', nargs='+',
            help='A list of debian distros. Default: %(default)s',
            default=['lucid', 'maverick', 'natty', 'oneiric'])

    parser.add_argument('--push', dest='push', help='Push it to your remote repo?', action='store_true')
    parser.add_argument('--first_release', dest='first_release', help='Is this your first release?', action='store_true')
    return parser.parse_args()


def call(working_dir, command, pipe=None):
    print('+ ' + ' '.join(command))
    process = Popen(command, stdout=pipe, cwd=working_dir)
    output, unused_err = process.communicate()
    retcode = process.poll()
    if retcode:
        raise CalledProcessError(retcode, command,
         output=output)
    if pipe:
        return output

def check_local_repo_exists(repo_path):
    return os.path.exists(os.path.join(repo_path, '.git'))

def update_repo(working_dir, repo_path, repo_uri, first_release):
    if check_local_repo_exists(repo_path):
        print("please start from a bare working dir::\n\trm -rf %s" % repo_path)
        sys.exit(1)
    if first_release:
        os.makedirs(repo_path)
        call(repo_path, ['git', 'init'])
        call(repo_path, ['git', 'remote', 'add', 'origin', repo_uri])
    else:
        command = ('gbp-clone', repo_uri);
        call(working_dir, command)

    command = ['git', 'config', '--add', 'remote.origin.push', '+refs/heads/*:refs/heads/*']
    call(repo_path, command)

    command = ['git', 'config', '--add', 'remote.origin.push', '+refs/tags/*:refs/tags/*']
    call(repo_path, command)

def novel_version(repo_path, version):
    tags = call(repo_path, ['git', 'tag'], pipe=subprocess.PIPE)
    if 'upstream/%s' % version in tags:
        return False
    return True

def import_orig(repo_path, upstream_tarball, version):
    if not novel_version(repo_path, version):
        print('Warning: removing previous upstream version %(version)s!'
                % locals(), file=sys.stderr)
        call(repo_path, ['git', 'tag', '-d', 'upstream/%(version)s' % locals()])
    upstream_tarball = os.path.abspath(upstream_tarball)
    if len(call(repo_path, ['git', 'diff'], pipe=subprocess.PIPE)):
        call(repo_path, ['git', 'commit', '-a', '-m', '"commit all..."'])
    call(repo_path, ['git', 'import-orig', upstream_tarball])

def make_working(working_dir):
    if not os.path.exists(working_dir):
        os.makedirs(working_dir)

def exclude(filename):
    if filename[-1] == '~':
        return True;
    return any(x == os.path.basename(filename) for x in ('.svn', '.git', '.hg'))

def filter(tarinfo):
    if exclude(tarinfo.name):
        return None
    return tarinfo

def make_tarball(upstream, tarball_name):
    tarball = tarfile.open(name=tarball_name, mode='w:gz')
    tarball.add(name=upstream, arcname=os.path.basename(upstream), recursive=True, exclude=exclude, filter=filter)
    tarball.close()

def sanitize_package_name(name):
    return name.replace('_', '-')

def parse_stack_yaml(upstream, rosdistro):
    yaml_path = os.path.join(upstream, 'stack.yaml')
    stack_yaml = yaml.load(open(yaml_path))

    if 'Catkin-ChangelogType' not in stack_yaml:
        stack_yaml['Catkin-ChangelogType'] = ''
    stack_yaml['DebianInc'] = '0'
    stack_yaml['Package'] = sanitize_package_name(stack_yaml['Package'])
    stack_yaml['ROS_DISTRO'] = rosdistro
    stack_yaml['INSTALL_PREFIX'] = '/opt/ros/%s' % rosdistro
    stack_yaml['PackagePrefix'] = 'ros-%s-' % rosdistro
    return stack_yaml

def template_dir():
    return os.path.join(os.path.dirname(__file__), 'em')

def expand(fname, stack_yaml, source_dir, dest_dir, filetype=''):
    #where normal templates live
    templatedir = template_dir()
    #the default input template file path
    ifilename = os.path.join(templatedir, fname)

    if filetype != '':
        if filetype.startswith('+'):
            ifilename = os.path.join(source_dir, filetype[1:])
        else:
            ifilename += ('.' + filetype + '.em')
    else:
        ifilename += '.em'

    print("Reading %s template from %s" % (fname, ifilename))
    file_em = open(ifilename).read()

    s = em.expand(file_em, **stack_yaml)

    ofilename = os.path.join(dest_dir, fname)
    ofilestr = open(ofilename, "w")
    print(s, file=ofilestr)
    ofilestr.close()
    if fname == 'rules':
        os.chmod(ofilename, 0755)

def generate_deb(stack_yaml, repo_path, stamp, debian_distro):
    stack_yaml['Distribution'] = debian_distro
    stack_yaml['Date'] = stamp.strftime('%a, %d %b %Y %T %z')
    stack_yaml['YYYY'] = stamp.strftime('%Y')

    source_dir = repo_path
    dest_dir = os.path.join(source_dir, 'debian')
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    #create control file:
    expand('control', stack_yaml, source_dir, dest_dir)
    expand('changelog', stack_yaml, source_dir, dest_dir, filetype=stack_yaml['Catkin-ChangelogType'])
    expand('rules', stack_yaml, source_dir, dest_dir, filetype=stack_yaml['Catkin-DebRulesType'])
    expand('copyright', stack_yaml, source_dir, dest_dir, filetype=stack_yaml['Catkin-CopyrightType'])
    
    ofilename = os.path.join(dest_dir, 'compat')
    ofilestr = open(ofilename, "w")
    print("8", file=ofilestr)
    ofilestr.close()

def commit_debian(stack_yaml, repo_path):
    call(repo_path, ['git', 'add', 'debian'])
    message = '''+ Creating debian mods for distro: %(Distribution)s, rosdistro: %(ROS_DISTRO)s, upstream version: %(Version)s
''' % stack_yaml
    call(repo_path, ['git', 'commit', '-m', message])

def gbp_sourcedebs(stack_yaml, repo_path, output):
    tag = '--git-debian-tag=debian/ros_%(ROS_DISTRO)s_%(Version)s_%(Distribution)s' % stack_yaml
    call(repo_path, ['git', 'buildpackage',
        '-S', '--git-export-dir=%s' % output,
        '--git-ignore-new', '--git-retag', '--git-tag', tag, '-uc', '-us'])
if __name__ == "__main__":
    stamp = datetime.datetime.now(dateutil.tz.tzlocal())

    args = parse_options()
    stack_yaml = parse_stack_yaml(args.upstream, args.rosdistro)
    make_working(args.working)

    tarball_name = '%(Package)s-%(Version)s.tar.gz' % stack_yaml
    tarball_name = os.path.join(args.working, tarball_name)

    repo_base, extension = os.path.splitext(os.path.basename(args.repo_uri))
    repo_path = os.path.join(args.working, repo_base)

    print('Generating an upstream tarball --- %s' % tarball_name)
    make_tarball(args.upstream,
                 tarball_name)


    #step 1. clone repo
    update_repo(working_dir=args.working, repo_path=repo_path, repo_uri=args.repo_uri, first_release=args.first_release)

    import_orig(repo_path, tarball_name, stack_yaml['Version'])

    for debian_distro in args.distros:
        generate_deb(stack_yaml, repo_path, stamp, debian_distro)
        commit_debian(stack_yaml, repo_path)
        gbp_sourcedebs(stack_yaml, repo_path, args.output)

    if args.push:
        call(repo_path, ['git', 'push'])
