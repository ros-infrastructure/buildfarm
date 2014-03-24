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


from optparse import OptionParser
import buildfarm.storm as storm
import time
import sys
import jenkins
import urllib2
import threading
from buildfarm.storm_helpers import get_slave_servers,\
    get_default_catkin_debs_config,\
    get_default_storm_config, load_config_from_file,\
    do_ssh_popen, do_ssh_paramiko, do_ssh, do_scp,\
    push_storm, generate_hostname, print_elapsed_time





parser = OptionParser()

parser.add_option('--do-no-destroy', dest='do_not_destroy', default=False)

parser.add_option('--storm-config-id', dest='storm_config_id', default='3',
                  help="config ids listed in list_machines.py.  3 = 2Gb VM, 6 = 32Gb VM")


jenkins_config = load_config_from_file(get_default_catkin_debs_config())
storm_config = load_config_from_file(get_default_storm_config())


(options, args) = parser.parse_args()
if len(args) != 1:
    parser.error("Need 1 argument of how many machines")

start_time = time.time()

number = int(args[0])
print "Requested to make %d machines" % number

config_id = int(options.storm_config_id)

sapi = storm.StormAPI(storm_config['storm_api_username'],
                      storm_config['storm_api_password'],
                      storm_config['storm_vm_root_password'])

servers = sapi.storm_server_list()

print "balance before", sapi.account_paymethod_balance()

print "%d servers preexisting" % len(servers)
slave_servers = get_slave_servers(servers)
num_others = len(servers) - len(slave_servers)
print "%d slave servers, %d others" % (len(slave_servers), num_others)

server_limit = sapi.account_limits_servers()
server_limit = 40
available_slots = server_limit - num_others
if number > available_slots:
    number = available_slots
    print "Scaling back request: only %d servers possible due to server limit %d and %d other machines"%(available_slots, server_limit, num_others)

number_of_new_machines = number - len(slave_servers)
print "adjusting number of machines by %d" % number_of_new_machines

print_elapsed_time(start_time)

# test destroy
#if len(servers) > 3:
#    for s in servers[:-3]:
#        print "destroying ", s
#        print "destroyed", sapi.storm_server_destroy(s['uniq_id'])




#servers = sapi.storm_server_list()
#print "%d servers"%len(servers)#, servers
#print "new servers:"
#for s in new_machines:
#    print s['domain']


# connect to jenkins
try:
    jenkins_inst = jenkins.Jenkins(jenkins_config['url'], jenkins_config['username'], jenkins_config['password'])
    # call the API to make sure we're authenticated.  This will except if the login is incorrect. 
    jobs = jenkins_inst.get_jobs()
except urllib2.URLError, ex:
    print "Failed to connect to server %s:"%jenkins_config['url'], ex
    sys.exit(1)
except jenkins.JenkinsException, ex:
    print "failed to connect to jenkins, not creating new jobs.  Please check username and password. ", ex
    sys.exit(1)


# Spin new machines
new_machines = []
if number_of_new_machines > 0:

    hostnames = [s['domain'] for s in servers]
    for i in range(number - len(slave_servers)):

        new_hostname = generate_hostname(hostnames, "storm.ros.org", server_limit)
        if not new_hostname:
            print "Failed to find a new hostname skipping new machine %d"%i
            continue
        hostnames.append(new_hostname)
        print "generating for host %s"%new_hostname

        with open(storm_config['storm_vm_public_keyfile']) as f:
            public_key = f.read().strip()


        new_m = sapi.storm_server_create_preconfig(new_hostname, config_id, public_key)
        print "new_m", new_m
        if new_m:
            if not 'error_class' in new_m:
                new_machines.append(new_m)
            else:
                print "ERROR:", new_m
        print_elapsed_time(start_time)
    if len(new_machines) > 0:
        print "Requested creation of machine %s"%new_machines[-1]['domain']
    else:
        print "no new machines created!!! Exiting!"
        sys.exit(0)
    print "balance after creations", sapi.account_paymethod_balance()


    new_ids = [s['uniq_id'] for s in new_machines]

    # Wait for new machines 
    print "wait_for_running of", new_ids
    pending_ids = new_ids
    while pending_ids:
        #todo Add overall timeout
        (running_new_ids, pending_ids, failed_ids) = sapi.wait_for_running(new_ids)
        print "waiting for running, started: %s pending: %s, failed: %s"%(running_new_ids, pending_ids, failed_ids)

        for sid in failed_ids:
            print "destroying %s because it failed to start"%sid

        successful_ips = []
        pushed_ids = {}
        for sid in running_new_ids:
            details = sapi.storm_server_details(sid)
            if 'ip' in details:
                # push the keys needed for puppet
                if push_storm(details['ip'],
                              details['domain'],
                              identity_dir=storm_config['storm_vm_identity_dir']):
                    successful_ips.append(details['ip'])
                    pushed_ids[details['ip']] = sid
                else:
                    print("error while pushing puppet keys to %s" % details['ip'])
                    failed_ids.append(sid)
            else:
                print "Cannot push settings. No IP for server. Destroying.", details
                failed_ids.append(sid)

        print "successfully setup ips", successful_ips

        def configure_slave(ip, status):
            puppetcommand = 'puppet apply /etc/puppet/manifests/site.pp'
            # puppetcommand="puppet agent --test --server puppet.ros.org"
            # Run puppet agent
            print('%-15s: calling puppet' % ip)
            ret = do_ssh_popen(ip, puppetcommand,
                               key_filename=storm_config['storm_vm_private_keyfile'])
            if ret & 1 or ret & 4:
                print("%-15s: errors occured during puppet configuration" % ip)
                status[ip] = False
                return

            # Stop client's puppet service. Re-stopping it, because --no-daemonize fails to do it's job.
            do_ssh_popen(ip, 'service puppet stop',
                         key_filename=storm_config['storm_vm_private_keyfile'])

            status[ip] = True

        threads = {}
        status = {}
        for ip in pushed_ids:
            print("launching slave configuration for ip %s" % ip)
            threads[ip] = threading.Thread(target=configure_slave, kwargs={'ip':ip, 'status':status})
            threads[ip].start()

        # wait for all threads to finish
        for ip, thr in threads.iteritems():
            thr.join()

        for ip in threads:
            if ip not in status or not status[ip]:
                print("configuration failed for slave %s" % ip)
                successful_ips.remove(ip)
                failed_ids.append(pushed_ids[ip])

        for ip in successful_ips:
            print("trying to register jenkins node for ip %s" % ip)
            try:
                node_name = ip
                jenkins_inst.create_node(node_name,
                                         numExecutors=1,
                                         nodeDescription="Standard ROS Build Slave",
                                         remoteFS='/home/rosbuild/hudson',
                                         labels='devel prerelease released debbuild doc',
                                         exclusive=True,
                                         launcher=jenkins.LAUNCHER_SSH,
                                         launcher_params={"host": ip,
                                                          "credentialsId": "722636cf-5333-4485-b288-3dae57e17c7b",
                                                          "port": "22" })
                print "Successfully registered jenkins node", node_name
            except jenkins.JenkinsException, ex:
                print "Failed to register Jenkins node: %s.  Exception: %s"%( node_name, ex)
                found_fail = False
                for sid in running_new_ids:
                    details = sapi.storm_server_details(sid)
                    if 'ip' in details and details['ip'] == ip:
                        print "IP matched failed configure, destorying instance", ip
                        failed_ids.append(sid)
                        found_fail = True
                        break
                if not found_fail:
                    print "Failed to find storm machine with matching IP of Jenkins failure. ", ip
        print_elapsed_time(start_time)

        # cleanup all failed ids
        if not options.do_not_destroy:
            for sid in failed_ids:
                print "Destroying %s as it failed to configure" % sid
                sapi.storm_server_destroy(sid)
        else:
            print('... did not actually destroy [%s].' % ", ".join(failed_ids),
                  'Please omit the --do-not-destroy option'
                  'if you want to destroy failed slaves')

elif number_of_new_machines < 0:
    destructions_required = -1 * number_of_new_machines
    destruction_queue = []
    destruction_skipped = []
    if destructions_required > 0:
        servers = sapi.storm_server_list()
        slave_servers = get_slave_servers(servers)

        # iterating slaves in order of time
        for sl in sorted(slave_servers, key=lambda machine: machine[u'create_date']):
            ip_str = sl[u'ip']
            if jenkins_inst.node_exists(ip_str):
                destruction_queue.append(sl)
                if len(destruction_queue) >= destructions_required:
                    break
            else:
                print("Skipping %s due to no exact match on jenkins. It must be customized." % ip_str)

        print("Are you sure you want to delete" 
              " these machines? %s" % \
                  ['<< ' + sl['ip'] + ' created on ' + \
                       sl['create_date'] + '>>' for sl in destruction_queue])
        print("You have 10 seconds to Ctrl-C to stop it")
        time.sleep(10)
        for sl in destruction_queue:
            ip_str = sl['ip']
            uid = sl['uniq_id']
            node_info = jenkins_inst.get_node_info("%s" % ip_str)
            if not node_info['idle']:
                print "Node %s %s not idle, SKIPPING DESTRUCTION" % (ip_str, uid)
                destruction_skipped.append(sl)
                continue
            # slave is idle: delete slave and destoy VM
            print "destroying %s %s" % (ip_str, uid)
            jenkins_inst.delete_node("%s" % ip_str)
            sapi.storm_server_destroy(uid)

        if len(destruction_skipped):
            print "Some destruction skipped", [sl['ip'] for sl in destruction_skipped] 

else:
    print "Number of machines same as requested doing nothing"




### TODO check pairings here
