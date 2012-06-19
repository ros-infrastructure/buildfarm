from __future__ import print_function

import os
import sys

from optparse import OptionParser

#from . import __version__
from .jenkins_support import load_server_config_file, get_default_catkin_debs_config, JenkinsConfig_to_handle
from .rosci_creator import process_jobs, load_jobs_from_file

NAME='rosci'

def rosci_main():
    #print("starting rosci %s"%__version__)
    parser = OptionParser(usage="usage: %prog <jobs.yaml> <rosdistro-name>", prog=NAME)
    parser.add_option("-n", dest="fake", action="store_true", help="Don't actually upload to Jenkins", default=False)
    options, args = parser.parse_args()
    if len(args) < 2:
        parser.error("please specify jobs.yaml file and ROS distribution name (e.g. fuerte)")

    jobs_yaml_path = args[0]
    if not os.path.isfile(jobs_yaml_path):
        parser.error("invalid jobs.yaml path: %s"%jobs_yaml_path)
    rosdistro_name = args[1]

    #TODO: this raises on failure
    server_config = load_server_config_file(get_default_server_config_file())
    jenkins_handle = JenkinsConfig_to_handle(server_config)
    jobs_data = load_jobs_from_file(jobs_yaml_path)

    process_jobs(jobs_data, jenkins_handle, rosdistro_name, options.fake)
    
