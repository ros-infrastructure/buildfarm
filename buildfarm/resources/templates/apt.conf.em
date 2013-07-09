@{import os}
Dir::Etc @os.path.join(rootdir, 'etc/apt');
Dir::State @os.path.join(rootdir, 'var/lib/apt');
Dir::Cache @os.path.join(rootdir, 'var/cache');
Dir::State::status @os.path.join(rootdir, 'var/lib/dpkg/status');
