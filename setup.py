#!/usr/bin/env python

from setuptools import setup

# Prevent "TypeError: 'NoneType' object is not callable" error
# when running `python setup.py test`
# (see http://www.eby-sarna.com/pipermail/peak/2010-May/003357.html)
try:
    import multiprocessing
except ImportError:
    pass

setup(
    name='buildfarm',
    version='0.0.1',
    packages=['buildfarm'],
    package_dir={'buildfarm': 'buildfarm'},
    scripts=[
        'scripts/assert_package_dependencies_present.py',
        'scripts/assert_package_present.py',
        'scripts/count_ros_packages.py',
        'scripts/create_release_jobs.py',
        'scripts/create_static_jobs.py',
        'scripts/generate_sourcedeb',
        'scripts/generate_status_page.py',
        'scripts/setup_apt_root.py',
        'scripts/trigger_missing.py'],
    package_data={'buildfarm': ['resources/templates/*.em', 'resources/templates/*/*']},
    install_requires=['argparse', 'catkin_pkg', 'EmPy', 'rospkg', 'vcstools'],
    author='Tully Foote',
    author_email='tfoote@willowgarage.com',
    url='http://www.ros.org/wiki/',
    download_url='http://pr.willowgarage.com/downloads/buildfarm/',
    keywords=['ROS'],
    classifiers=[
        'Programming Language :: Python',
        'License :: OSI Approved :: BSD License'],
    description='ROS package library',
    long_description='''\
A library for interacting with the catkin buildfarm.
''',
    license='BSD'
)
