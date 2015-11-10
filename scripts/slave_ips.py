#!/usr/bin/env python

import buildfarm.storm as storm
from buildfarm.storm_helpers import get_slave_servers


from buildfarm.storm_helpers import get_slave_servers,\
    get_default_storm_config, get_slave_servers,\
    get_default_catkin_debs_config,\
    get_default_storm_config, load_config_from_file,\
    do_ssh_popen, do_ssh_paramiko, do_ssh, do_scp,\
    push_storm, generate_hostname, print_elapsed_time

storm_config = load_config_from_file(get_default_storm_config())
sapi = storm.StormAPI(storm_config['storm_api_username'],
                      storm_config['storm_api_password'],
                      storm_config['storm_vm_root_password'])

servers = sapi.storm_server_list()
slaves = get_slave_servers(servers)

ips = [s['ip'] for s in slaves if 'ip' in s]
print ' '.join(ips)
