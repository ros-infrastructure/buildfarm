@{import os}
Dir::Etc @os.path.join(rootdir, 'etc/apt');
Dir::State @os.path.join(rootdir, 'var/lib/apt');
Apt::Archives::MaxSize "10000";  # In Mb  trying out parameter from http://askubuntu.com/questions/51567/why-does-var-cache-apt-archives-keep-deleting-files