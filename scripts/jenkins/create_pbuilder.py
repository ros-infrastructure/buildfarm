#!/usr/bin/env python

from __future__ import print_function
import os
from xml.sax.saxutils import escape

from create_sourcedeb import common_options, Templates, expand, create_jenkins

def parse_options():
    import argparse
    parser = argparse.ArgumentParser(description='Create a jenkins job for setting up pbuilder roots.')
    common_options(parser)
    return parser.parse_args()

def job_name(d):
    return "pbuilder_create_%(ROS_DISTRO)s_%(DISTRO)s" % d

def create_config(d):
    #Create the bash script the runs inside the job
    #need the command to be safe for xml.
    script = os.path.join(Templates.template_dir, 'pbuilder_create.sh') #A config.xml template for something that runs a shell script
    d['COMMAND'] = escape(expand(script, d))
    #Now expand the configuration xml
    return expand(Templates.config_bash_template, d)

if __name__ == "__main__":
    args = parse_options()
    d = dict(
    ROS_DISTRO=args.rosdistro,
    DISTROS=args.distros,
    FQDN=args.fqdn,
    ROS_PACKAGE_REPO="http://50.28.27.175/repos/building"
    )
    for x in args.distros:
        d['DISTRO'] = x
        config = create_config(d)
        jb = job_name(d)
        if args.commit:
            create_jenkins(jb, config)
        else:
            print(config, "\n\n*****************************")
            print("Would have created job: %s " % jb)
            print("--commit to do it for real.")
