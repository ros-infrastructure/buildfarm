#!/usr/bin/env python

import subprocess
import tempfile
import shutil
import os

from construct_graph import topological_sort, buildable_graph_from_dscs

def deb_job_graph(dscs):
    """ Parse all dsc files in the tree and build them into the graph"""
    dsc_list = []
    for subdir, _, files in os.walk(dscs):
        dsc_list += [os.path.join(subdir, f) for f in files if os.path.splitext(f)[1] in '.dsc']
    graph = buildable_graph_from_dscs(dsc_list)
    return graph


def build_graph(repo, dscs_path = None):
    """ Pull down all the dsc files from the repo and then build the graph"""
    graph = None
    if dscs_path:
        graph = deb_job_graph(dscs_path)
    try:
        print "please be patient downloading all dscs from repo %s"%repo
        tempdir = tempfile.mkdtemp()
        cmd = "wget -r %s/pool/main -A dsc -nd --directory-prefix=%s"%(repo, tempdir)
        subprocess.check_call(cmd.split(), stdout=open("/dev/null", "w"), stderr = subprocess.STDOUT)
        graph = deb_job_graph(tempdir)
    finally:
        shutil.rmtree(tempdir)

    return graph
    

if __name__ == "__main__":
    print build_graph("http://50.28.27.175/repos/building")
