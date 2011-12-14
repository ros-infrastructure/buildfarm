Source: @(PackagePrefix)@(Package)
Section: @(Section)
Priority: @(Priority)
Maintainer: @(Maintainer)
Build-Depends: @(empy.expand(locals()['Build-Depends'], locals()))
Homepage: @(Homepage)

Package: @(PackagePrefix)@(Package)
Architecture: @(Architecture)
Depends: @(empy.expand(locals()['Depends'], locals()))
Description: @(Description)

