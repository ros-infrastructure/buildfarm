git buildpackage conventions
============================
The conventions for the git buildpackage repos are listed bellow.

Patterns
--------

tags will be used to mark points in the git repo with which source debs are generated.

Here is some regex for ros specific git tags, using python. Regex:``debian/ros_(.+)_(\d+\.\d+\.\d+)_(.+)``

.. code-block:: python
  
  import re,subprocess
  tags = subprocess.check_output(['git','tag']).split('\n')
  for x in tags:
    m = re.search('debian/ros_(.+)_(\d+\.\d+\.\d+)_(.+)', tag)
    print m.groups

* **group 1** is the ros distribution short name, e.g. fuerte, galapagos, H.
* **group 2** is the upstream package version.  X.Y.Z
* **group 3** is the ubuntu or debian distro, e.g. natty, oneiric, etc...

This tag is create by the python format string

.. code-block:: python
  
  'debian/ros_%(ROS_DISTRO)s_%(Version)s_%(Distribution)s'