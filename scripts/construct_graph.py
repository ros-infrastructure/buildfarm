#!/usr/bin/env python

from urlgrabber import urlread
import pprint, apt.debfile, apt_pkg, sys, pprint

thegraph = {}
our_packages = set()

for dscfilename in sys.argv[1:]:

    dsc = apt.debfile.DscSrcPackage(dscfilename)
    # print dsc.depends
    ctrl = apt_pkg.TagFile(open(dscfilename))
    ctrl.next()
    #print section
    name = ctrl.section['Source']
    our_packages.add(name)
    deps = apt_pkg.parse_depends(ctrl.section['Build-Depends'])
    print deps
    for [(pkg, version, relation)] in deps:
        print pkg, version, relation
        s = thegraph.get(pkg, set([]))
        s.add(name)
        thegraph[pkg] = s


print thegraph

allpkgs = thegraph.keys()

for k in allpkgs:
    if k not in our_packages:
        del thegraph[k]

print "*\n"*5
pprint.pprint(thegraph)
