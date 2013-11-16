#TODO License

import os
import subprocess
import buildfarm.apt_root
from tempfile import NamedTemporaryFile

default_mirror = 'http://us.archive.ubuntu.com/ubuntu'
arm_mirror = 'http://ports.ubuntu.com/ubuntu-ports'
repo_urls = ['ros@http://50.28.27.175/repos/building']


#build_command = ['cowbuilder']
build_command = ['sudo', 'pbuilder']
#build_command = ['pbuilder']

def get_mirror(arch):
    if arch in ['armel', 'armhf']:
        return arm_mirror
    return default_mirror

def get_debootstrap_type(arch):
    if arch in ['armel', 'armhf']:
        return 'qemu-debootstrap'
    return 'debootstrap'


def run(cmd):
    try:
        print ' '.join(cmd)
        subprocess.check_call(cmd)
    except:
        return False
    return True


class PbuilderrcTempfile(object):
    def __init__(self, key_values):

        def add(key, value):
            return "%s=%s\n" % (key, value)
        content = ""
        for k, v in key_values.items():
            content += add(k, v)
        self._tempfile = NamedTemporaryFile()
        self._tempfile.write(content)
        self._tempfile.flush()
        print "pbuilder config", self._tempfile.name, "with:"
        for l in content.splitlines():
            print "- %s" % l

    def __enter__(self):
        return self._tempfile.name

    def __exit__(self, type, value, tb):
        pass


class PbuilderRunner(object):
    def __init__(self, root, codename, arch, image_number=0,
                 mirror=default_mirror,
                 debootstrap_type='debootstrap',
                 keyring='/etc/apt/trusted.gpg'):
        self._root = root
        self._codename = codename
        self._arch = arch
        self._image_number = image_number

        self._mirror = mirror
        self._debootstrap_type = debootstrap_type
        self._keyring = keyring

        self.base_path = os.path.join(root, codename, arch)
        self._apt_conf_dir = os.path.join(self.base_path, 'etc', 'apt')
        self._aptcache_dir = os.path.join(self.base_path, 'aptcache')
        self._ccache_dir = os.path.join(self.base_path, 'ccache')
        self._build_dir = os.path.join(self.base_path, 'build')
        self.base_tarball_filename = os.path.join(self.base_path,
                                                  "base-%s.tar.gz" %\
                                                      image_number)

    def update(self):
        ros_repos = buildfarm.apt_root.parse_repo_args(repo_urls)
        buildfarm.apt_root.setup_apt_rootdir(self.base_path,
                                             self._codename,
                                             self._arch,
                                             mirror=self._mirror,
                                             additional_repos=ros_repos)


        pb_args = {}
        pb_args['BUILDPLACE'] = self._build_dir
        pb_args['APTCACHE'] = self._aptcache_dir
        pb_args['CCACHEDIR'] = self._ccache_dir
        pb_args['AUTOCLEANAPTCACHE'] = 'yes'
        pb_args['BASETGZ'] = self.base_tarball_filename

        with PbuilderrcTempfile(pb_args) as conffile:
            cmd = build_command + \
                ["--update",
                 "--configfile", conffile]
            return run(cmd)

    def check_present(self):
        """
        Check if this chroot is setup and up to date
        """
        return os.path.exists(self.base_tarball_filename)

    def verify_up_to_date(self):
        """
        Create if not present otherwise update.
        """
        if not self.check_present():
            return self.create()
        else:
            return self.update()

    def create(self):
        """
        Create the base tarball
        """
        if self.check_present():
            return False
        if not os.path.isdir(self.base_path):
            os.makedirs(self.base_path)

        if not os.path.isdir(self._aptcache_dir):
            os.makedirs(self._aptcache_dir)

        if not os.path.isdir(self._build_dir):
            os.makedirs(self._build_dir)

        ros_repos = buildfarm.apt_root.parse_repo_args(repo_urls)
        buildfarm.apt_root.setup_apt_rootdir(self.base_path,
                                             self._codename,
                                             self._arch,
                                             mirror=self._mirror,
                                             additional_repos=ros_repos)
        pb_args = {}
        pb_args['APTCONFDIR'] = self._apt_conf_dir
        pb_args['ARCHITECTURE'] = self._arch
        pb_args['BASETGZ'] = self.base_tarball_filename
        pb_args['DISTRIBUTION'] = self._codename
        pb_args['BUILDPLACE'] = self._build_dir
        pb_args['APTCACHE'] = self._aptcache_dir
        pb_args['CCACHEDIR'] = self._ccache_dir
        pb_args['MIRROR'] = self._mirror
        pb_args['KEYRING'] = self._keyring
        pb_args['DEBOOTSTRAP'] = self._debootstrap_type
        pb_args['DEBOOTSTRAPOPTS'] = "( '--arch=%s' '--keyring=%s' )" % \
            (self._arch, self._keyring)
        with PbuilderrcTempfile(pb_args) as conffile:
            cmd = build_command + ['--create',
                                   "--configfile", conffile]
            result = run(cmd)

        if not result:
            if os.path.exists(self.base_tarball_filename):
                os.remove(self.base_tarball_filename)

        return result

    def execute(self, filename):
        if not self.check_present():
            return False
        pb_args = {}
        pb_args['BASETGZ'] = self.base_tarball_filename
        pb_args['BUILDPLACE'] = self._build_dir
        with PbuilderrcTempfile(pb_args) as conffile:
            cmd = build_command + ['--execute',
                                   "--configfile", conffile,
                                   filename]
            return run(cmd)

    def build(self, dsc_filename, output_dir, hookdir=""):
        pb_args = {}
        pb_args['BASETGZ'] = self.base_tarball_filename
        pb_args['DISTRIBUTION'] = self._codename
        pb_args['BUILDPLACE'] = self._build_dir
        pb_args['APTCACHE'] = self._aptcache_dir
        pb_args['CCACHEDIR'] = self._ccache_dir
        pb_args['HOOKDIR'] = hookdir
        pb_args['BUILDRESULT'] = output_dir
        pb_args['DEBBUILDOPTS'] = '-b'


        # pb_args['APTCONFDIR'] = self._apt_conf_dir

        with PbuilderrcTempfile(pb_args) as conffile:
            cmd = build_command + \
                ['--build',
                 '--configfile', conffile,
                 dsc_filename]
        return run(cmd)


if __name__ == "__main__":
    print "running pbuilder test"

    test_as = PbuilderRunner(root='/tmp/test',
                             codename='trusty',
                             arch='amd64',
                             image_number=1)

    #test_as.create()

    #test_as.update()

    test_as.verify_up_to_date()
    test_as.execute('/tmp/hello_world.bash')

    #test_as.build('/tmp/src/ros-hydro-roscpp_1.9.50-0precise.dsc',
    #              '/tmp/output')
