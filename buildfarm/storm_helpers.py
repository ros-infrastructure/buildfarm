#!/usr/bin/env python

# Software License Agreement (BSD License)
#
# Copyright (c) 2014 Open Source Robotics Foundation
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Open Source Robotics Foundation nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import os
import sys
import yaml
import subprocess
import paramiko
import stat
import time


class SSHOpenConn:
    ssh_conn = {}


def get_slave_servers(server_list):
    slave_servers = []
    for s in server_list:
        try:

            if 'storm.ros.org' in s['domain']:
                slave_servers.append(s)

            elif 'storm.willowgarage.com' in s['domain']:
                slave_servers.append(s)
            else:
                print >>sys.stderr, "%s not a slave: ignoring"%s['domain']
        except:
            print >>sys.stderr, "server doesn't have domain:", s
    return slave_servers


def get_default_catkin_debs_config():
    #stolen from buildfarm.jenkins_support
    import rospkg.environment
    return os.path.join(rospkg.environment.get_ros_home(), 'buildfarm', 'server.yaml')


def get_default_storm_config():
    import rospkg.environment
    return os.path.join(rospkg.environment.get_ros_home(), 'buildfarm', 'storm.yaml')


def load_config_from_file(server_config_file):
    if not os.path.isfile(server_config_file):
        raise RuntimeError("server config file [%s] does not exist" % server_config_file)

    with open(server_config_file) as f:
        server = yaml.load(f.read())
    return server


def run_cmd(cmd, quiet=True, extra_args=None, feed=None):
    args = {'shell': True}
    if quiet:
        args['stderr'] = args['stdout'] = subprocess.PIPE
    if feed is not None:
        args['stdin'] = subprocess.PIPE
    if extra_args is not None:
        args.update(extra_args)
    p = subprocess.Popen(cmd, **args)
    if feed is not None:
        p.communicate(feed)
    return p.wait()


def ssh_cmd(host, user='root', key_filename='identity/id_rsa'):
    sshoption = "-o StrictHostKeyChecking=no -i %s" % key_filename
    sshuserhost = user + "@" + host
    return "ssh " + sshoption + " " + sshuserhost


def do_ssh_popen(host, cmd, user='root', feed=None,
                 key_filename='identity/id_rsa'):
    return run_cmd(ssh_cmd(host,
                           user=user,
                           key_filename=key_filename) + ' ' + cmd,
                   feed=feed)


def do_ssh_paramiko(host, cmd, user='root', feed=None,
                    key_filename='identity/id_rsa'):
    if host not in SSHOpenConn.ssh_conn:
        s = paramiko.SSHClient()
        s.set_missing_host_key_policy(paramiko.WarningPolicy())
        s.connect(host, username=user, key_filename=key_filename)
        SSHOpenConn.ssh_conn[host] = s

    s = SSHOpenConn.ssh_conn[host]
    c = s.get_transport().open_session()
    c.exec_command(cmd)
    if feed is not None:
        stdin = c.makefile('wb')
        stdin.write(feed)
        stdin.flush()
    c.shutdown_write()
    c.set_combine_stderr(True)
    stdout = c.makefile('r')
    buf = stdout.read()
    while buf != '':
        print(buf)  # uncomment this line if you want to debug
        buf = stdout.read()
    return c.recv_exit_status()


def do_ssh(host, cmd, user='root', feed=None, key_filename='identity/id_rsa'):
    return do_ssh_paramiko(host, cmd, user=user, feed=feed,
                           key_filename=key_filename)


def do_scp(host, filename, remote_filename, user='root',
           mode=stat.S_IRUSR | stat.S_IWUSR, key_filename='identity/id_rsa'):
    if host not in SSHOpenConn.ssh_conn:
        s = paramiko.SSHClient()
        s.set_missing_host_key_policy(paramiko.WarningPolicy())
        s.connect(host, username=user, key_filename=key_filename)
        SSHOpenConn.ssh_conn[host] = s

    s = SSHOpenConn.ssh_conn[host]
    sftp = s.open_sftp()
    sftp.put(filename, remote_filename)
    sftp.chmod(remote_filename, mode)
    sftp.close()
    return True


def push_storm(ip, hostname, identity_dir='identity'):
    """
    Gets keys from the puppet master, pushes them to the slave,
    and installs puppet
    """

    key_filename = os.path.join(identity_dir, 'id_rsa')

    print "push key filename", key_filename
    # do stuff with slave
    # first, install puppet
    print "updating apt"
    if do_ssh(ip, 'apt-get update', key_filename=key_filename):
        print "Failed to apt-get update, sometimes we collide with"\
            " another process on the dpkg-lock." \
            " Sleeping and retrying in 30 seconds"
        time.sleep(30)
        # retry we're seeing a collision on the dpkg lock file.
        # It appears apt-get update is automatically run on boot.
        if do_ssh(ip, 'apt-get update', key_filename=key_filename):
            return False
    print "installing puppet and git"
    if do_ssh(ip, 'apt-get install -y puppet git-core',
              key_filename=key_filename):
        return False

    print "stopping puppet"
    # stop puppet
    if do_ssh(ip, 'service puppet stop', key_filename=key_filename):
        return False

    print "copying key"
    do_scp(ip, os.path.join(identity_dir, 'id_rsa'),
           '/root/.ssh/id_rsa', key_filename=key_filename)

    print "adding github known_hosts"
    do_scp(ip, os.path.join(identity_dir, 'known_hosts'),
           '/root/.ssh/known_hosts', key_filename=key_filename)

    print "adding ssh config"
    do_scp(ip, os.path.join(identity_dir, 'ssh_config'),
           '/root/.ssh/config', key_filename=key_filename)

    print "Clearing /etc/puppet"
    if do_ssh(ip, 'rm -rf /etc/puppet', key_filename=key_filename):
        return False

    print "cloning puppet repo"
    if do_ssh(ip,
              'git clone git@github.com:wg-buildfarm/puppet.git /etc/puppet',
              key_filename=key_filename):
        return False

    print "Copying cron rule"
    do_scp(ip, os.path.join(identity_dir, 'cron.puppet'),
           '/etc/cron.d/puppet', key_filename=key_filename)

    # moved into threading in manage.py TODO move it back here and
    # call push_storm inside the threaded portion of manage.py

    # TODO: catch some more errors
    return True


def generate_hostname(existing_hostnames, template, value_range):
    # Iterate over all possible server names using the template and a numeric addition
    for j in range(value_range):
        potential_hostname="host%02d.%s" % (j, template)
        #print "evaluating potential", potential_hostname
        match = False
        for s in existing_hostnames:
            #print "  comparing to", s
            if s == potential_hostname:
                match = True
                #print "Match"
                continue

        if match == False:
            return potential_hostname
    return None


def print_elapsed_time(start_time):
    print "Elapsed time: %s seconds" % (time.time() - start_time)
