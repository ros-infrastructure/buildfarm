#!/usr/bin/env python

import yaml
import sys
import pprint
import re
import os
def parse_dsc(package_name, version, debian_version, dsc_file):
    dsc = yaml.load(open(dsc_file))
    return {(package_name, version):set([dep.strip() for dep in dsc['Build-Depends'].split(',')])}

def split_dsc(dsc):
    dsc_base = os.path.basename(dsc)
    m = re.search('(.+)_([\d\.]+)-(.+)\.dsc', dsc_base)
    package_name = m.group(1)
    version = tuple([int(x) for x in m.group(2).split('.')])
    debian_version = m.group(3)
    return (package_name, version, debian_version, dsc)

def sort_dscs(dscs):
    dscs_parsed = [ split_dsc(x) for x in dscs]
    dscs_parsed = sorted(dscs_parsed)
    dscs_parsed.reverse()
    
    latest_list = set()
    for package_name, version, debian_version, dsc in dscs_parsed:
        latest_list.add(package_name)
    return dscs_parsed

def buildable_graph_from_dscs(dscs):
    dscs = sort_dscs(dscs)
    graph = {}
    for x in dscs:
        graph.update(parse_dsc(*x))

    ourpackages = [package for package, version in graph.keys()]
    graph_we_can_build = {}
    
    for key, deps in graph.iteritems():
        graph_we_can_build[key] = deps.intersection(ourpackages)
    return graph_we_can_build
            

def topological_sort(graph):
    '''
    http://en.wikipedia.org/wiki/Topological_sorting
    L <- Empty list that will contain the sorted elements
    S <- Set of all nodes with no incoming edges
    while S is non-empty do
        remove a node n from S
        insert n into L
        for each node m with an edge e from n to m do
            remove edge e from the graph
            if m has no other incoming edges then
                insert m into S
    if graph has edges then
        return error (graph has at least one cycle)
    else 
        return L (a topologically sorted order)
    '''
    L = []
    S = [x for x, version in graph.keys() if len(graph[x, version]) == 0]
    while S:
        n = S.pop()
        L.append(n)
        for m, version in [(m, version) for m, version in graph.keys() if n in graph[m, version]]:
            graph[m, version].remove(n)
            if len(graph[m, version]) == 0:
                S.append(m)
    return L


if __name__ == "__main__":
    graph = buildable_graph_from_dscs(sys.argv[1:])
    pprint.pprint(graph)
    jobs = topological_sort(graph)
    pprint.pprint(jobs)
