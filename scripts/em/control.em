Source: @(PackagePrefix)@(Package)
Section: @(Section)
Priority: @(Priority)
Maintainer: @(Maintainer)
Build-Depends: debhelper (>= 7), @(empy.expand(locals()['Build-Depends'], locals()))
Homepage: @(Homepage)
Standards-Version: 3.9.2

Package: @(PackagePrefix)@(Package)
Architecture: @(Architecture)
Depends: ${shlibs:Depends}, ${misc:Depends}, @(empy.expand(locals()['Depends'], locals()))
Description: @(Description)
