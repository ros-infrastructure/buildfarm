#!/usr/bin/env python

import csv
import os
import logging
import re
import sys
import urllib2
import yaml

import apt
import numpy as np

import buildfarm.apt_root
import buildfarm.rosdistro
from rospkg.distro import distro_uri

ros_repos = {'ros': 'http://packages.ros.org/ros/ubuntu/',
             'shadow-fixed': 'http://packages.ros.org/ros-shadow-fixed/ubuntu/',
             'building': 'http://50.28.27.175/repos/building'}

version_rx = re.compile(r'[0-9.-]+[0-9]')

def get_repo_da_caches(rootdir, ros_repo_names, da_strs):
    '''
    Returns [(repo_name, da_str, cache_dir), ...]

    For example, get_repo_da_caches('/tmp/ros_apt_caches', ['ros', 'shadow-fixed'], ['quantal_i386'])
    '''
    return [(ros_repo_name, da_str, get_repo_cache_dir_name(rootdir, ros_repo_name, da_str))
            for ros_repo_name in ros_repo_names
            for da_str in da_strs]

def get_apt_cache(dirname):
    c = apt.Cache(rootdir=dirname)
    c.open()
    return c

def get_ros_repo_names(ros_repos):
    return ros_repos.keys()

def get_da_strs(distro_arches):
    return [get_dist_arch_str(d, a) for d, a in distro_arches]

bin_arches = ['amd64', 'i386']

def get_distro_arches(arches, rosdistro):
    distros = buildfarm.rosdistro.get_target_distros(rosdistro)
    return [(d, a) for d in distros for a in arches]

def make_versions_table(ros_pkgs_table, repo_name_da_to_pkgs, da_strs, repo_names, rosdistro):
    '''
    Returns an in-memory table with all the information that will be displayed:
    ros package names and versions followed by debian versions for each
    distro/arch.
    '''
    left_columns = [('name', object), ('version', object), ('wet', bool)]
    right_columns = [(da_str, object) for da_str in da_strs]
    columns = left_columns + right_columns
    table = np.empty(len(ros_pkgs_table), dtype=columns)

    for i, (name, version, wet) in enumerate(ros_pkgs_table):
        table['name'][i] = name
        table['version'][i] = version
        table['wet'][i] = wet
        for da_str in da_strs:
            versions = []
            for j, repo_name in enumerate(repo_names):
                v = get_pkg_version(da_str, repo_name_da_to_pkgs, repo_name, name, rosdistro)
                v = str(v)
                v = strip_version_suffix(v)
                versions.append(v)

            table[da_str][i] = '|'.join(versions)

    return table

def strip_version_suffix(version):
    """
    Removes trailing junk from the version number.

    >>> strip_version_suffix('')
    ''
    >>> strip_version_suffix('None')
    'None'
    >>> strip_version_suffix('1.9.9-0quantal-20121115-0529-+0000')
    '1.9.9-0'
    >>> strip_version_suffix('1.9.9-foo')
    '1.9.9'
    """
    match = version_rx.search(version)
    return match.group(0) if match else version

def get_pkg_version(da_str, repo_name_da_to_pkgs, repo_name, name, rosdistro):
    deb_name = buildfarm.rosdistro.debianize_package_name(rosdistro, name)
    if da_str.endswith('source'):
        # Get the source version from the corresponding amd64 package.
        amd64_da_str = da_str.replace('source', 'amd64')
        p = get_matching_pkg(repo_name_da_to_pkgs, deb_name, repo_name, amd64_da_str)
        return getattr(getattr(p, 'candidate', None), 'source_version', None)
    else:
        p = get_matching_pkg(repo_name_da_to_pkgs, deb_name, repo_name, da_str)
        return getattr(getattr(p, 'candidate', None), 'version', None)

def get_matching_pkg(repo_name_da_to_pkgs, deb_name, repo_name, da_str):
    pkgs = repo_name_da_to_pkgs.get((repo_name, da_str), [])
    matching_pkgs = [p for p in pkgs if p.name == deb_name]
    if not matching_pkgs:
        logging.debug('No package found with name %s on %s repo, %s',
                      deb_name, repo_name, da_str)
        return None
    elif len(matching_pkgs) > 1:
        logging.warn('More than one package found with name %s on %s repo, %s',
                     deb_name, repo_name, da_str)
        return None
    else:
        return matching_pkgs[0]

def get_ros_pkgs_table(wet_names_versions, dry_names_versions):
    return np.array(
        [(name, version, True) for name, version in wet_names_versions] + 
        [(name, version, False) for name, version in dry_names_versions],
        dtype=[('name', object), ('version', object), ('wet', bool)])

def get_dist_arch_str(d, a):
    return "%s_%s" % (d, a)

def get_repo_cache_dir_name(rootdir, ros_repo_name, dist_arch):
    return os.path.join(rootdir, ros_repo_name, dist_arch)

def build_repo_caches(rootdir, ros_repos, distro_arches):
    '''
    Builds (or rebuilds) local caches for ROS apt repos.

    For example, build_repo_caches('/tmp/ros_apt_caches', ros_repos,
                                   get_distro_arches())
    '''
    for repo_name, url in ros_repos.items():
        for distro, arch in distro_arches:
            dist_arch = get_dist_arch_str(distro, arch)
            dir = get_repo_cache_dir_name(rootdir, repo_name, dist_arch)
            build_repo_cache(dir, repo_name, url, distro, arch)

def build_repo_cache(dir, ros_repo_name, ros_repo_url, distro, arch):
    logging.info('Setting up an apt directory at %s', dir)
    repo_dict = {ros_repo_name: ros_repo_url}
    buildfarm.apt_root.setup_apt_rootdir(dir, distro, arch,
                                         additional_repos=repo_dict)
    logging.info('Getting a list of packages for %s-%s', distro, arch)
    cache = apt.Cache(rootdir=dir)
    cache.open()
    cache.update()
    # Have to open the cache again after updating.
    cache.open()

def get_wet_names_versions(rosdistro):
    rd = buildfarm.rosdistro.Rosdistro(rosdistro)
    return sorted([(name, rd.get_version(name, full_version=True)) for name in rd.get_package_list()],
                  key=lambda (name, version): name)

def get_dry_names_versions(rosdistro):
    return get_names_versions(get_dry_names_packages(rosdistro))

def get_names_versions(names_pkgs):
    return sorted([(name, d.get('version')) for name, d in names_pkgs],
                  key=lambda (name, version): name)


def get_dry_names_packages(rosdistro):
    '''
    Fetches a yaml file from the web and returns a list of pairs of the form

    [(short_pkg_name, pkg_dict), ...]

    for the dry (rosbuild) packages.
    '''
    
    dry_yaml = yaml.load(urllib2.urlopen(distro_uri(rosdistro)))
    return [(name, d) for name, d in dry_yaml['stacks'].items() if name != '_rules']

def get_pkgs_from_apt_cache(cache_dir, substring):
    cache = apt.Cache(rootdir=cache_dir)
    cache.open()
    return [cache[name] for name in cache.keys() if substring in name]

def render_csv(rootdir, outfile, rosdistro):
    arches = bin_arches + ['source']
    da_strs = get_da_strs(get_distro_arches(arches, rosdistro))
    ros_repo_names = get_ros_repo_names(ros_repos)
    repo_da_caches = get_repo_da_caches(rootdir, ros_repo_names, da_strs)
    wet_names_versions = get_wet_names_versions(rosdistro)
    dry_names_versions = get_dry_names_versions(rosdistro)
    ros_pkgs_table = get_ros_pkgs_table(wet_names_versions, dry_names_versions)

    # Get the version of each Debian package in each ROS apt repository.
    repo_name_da_to_pkgs = dict(((repo_name, da_str), get_pkgs_from_apt_cache(cache, 'ros-%s'%rosdistro))
                                for repo_name, da_str, cache in repo_da_caches)

    # Make an in-memory table showing the latest deb version for each package.
    t = make_versions_table(ros_pkgs_table, repo_name_da_to_pkgs, da_strs,
                            ros_repos.keys(), rosdistro)

    with open(outfile , 'w') as fh:

        # Output CSV from the in-memory table
        w = csv.writer(fh)
        w.writerow(t.dtype.names) 
        for row in t:
            w.writerow(row)


def transform_csv_to_html(data_source, metadata_builder):
    reader = csv.reader(data_source, delimiter=',', quotechar='"')
    rows = [row for row in reader]

    header = rows[0]
    rows = rows[1:]

    # move source columns before amd64/i386 columns for each distro
    column_mapping = {3: 5, 4: 3, 5: 4, 6: 8, 7: 6, 8: 7, 9: 11, 10: 9, 11: 10}
    header = [header[column_mapping[i] if column_mapping and i in column_mapping else i] for i in range(len(header))]
    rows = [[row[column_mapping[i] if column_mapping and i in column_mapping else i] for i in range(len(header))] for row in rows]

    html_head = make_html_head()

    metadata_columns = [None] * 3 + [metadata_builder(c) for c in header[3:]]
    header = [format_header_cell(header[i], metadata_columns[i]) for i in range(len(header))]

    # count non-None rows per (sub-)column
    footer = [[]] * 3 + [[0] * 3 for c in header[3:]]
    for row in rows:
        for i in range(3, len(footer)):
            versions = get_cell_versions(row[i])
            for j in range(0, len(versions)):
                if versions[j] != 'None':
                    footer[i][j] += 1

    rows = [format_row(r, metadata_columns) for r in rows]
    body = make_html_legend()
    body += make_html_table(header, footer, rows)

    return make_html_doc(html_head, body)


def format_header_cell(cell, metadata):
    if metadata and 'column_label' in metadata:
        cell = metadata['column_label']
    return cell


def format_row(row, metadata_columns):
    latest_version = row[1]
    is_wet = is_wet_package(row)
    public_changing_on_sync = [c for c in row[3:] if is_public_changing_on_sync(c)]
    public_regression_on_sync = [c for c in row[3:] if is_public_regression_on_sync(c)]
    has_diff_between_rosdistros = row[3] != row[6] or row[3] != row[9] or row[4] != row[7] or row[4] != row[10] or row[5] != row[8] or row[5] != row[11]

    # urls for each building repository column
    metadata = [None] * 3 + [md for md in metadata_columns[3:]]
    if not is_wet:
        metadata[3] = metadata[6] = metadata[9] = None
    job_urls = [md['job_url'].format(pkg=row[0].replace('_', '-')) if md else None for md in metadata]

    row = row[:2] + ['wet' if is_wet else 'dry'] + [format_versions_cell(row[i], latest_version, job_urls[i]) for i in range(3, len(row))]
    if has_diff_between_rosdistros:
        row[0] += ' <span class="hiddentext">diff</span>'

    if public_changing_on_sync:
        row[0] += ' <span class="hiddentext">sync</span>'

    if public_regression_on_sync:
        row[0] += ' <span class="hiddentext">regression</span>'

    return row


def is_public_changing_on_sync(cell):
    versions = get_cell_versions(cell)
    return versions[1] != versions[2]


def is_public_regression_on_sync(cell):
    versions = get_cell_versions(cell)
    return versions[1] == 'None' and versions[2] != 'None'


def get_cell_versions(cell):
    return cell.split('|')


def is_wet_package(row):
    return row[2] == 'True'


def format_versions_cell(cell, latest_version, url=None):
    repos = ['building', 'shadow-fixed', 'ros/public']
    versions = get_cell_versions(cell)
    return '&nbsp;'.join([format_version(v, latest_version, r, url if r == 'building' else None) for v, r in zip(versions, repos)])


def format_version(version, latest, repo, url=None):
    label = '%s: %s' % (repo, version)
    if latest:
        color = {'None': 'pkgMissing', latest: 'pkgLatest'}.get(version, 'pkgOutdated')
        # use reasonable names (even if invisible) to be searchable
        order_value = {'None': '5&nbsp;red', latest: '1&nbsp;green'}.get(version, '3&nbsp;blue')
    else:
        color = {'None': 'pkgIgnore'}.get(version, 'pkgObsolete')
        # use reasonable names (even if invisible) to be searchable
        order_value = {'None': '2&nbsp;gray'}.get(version, '4&nbsp;yellow')
    if url:
        order_value = '<a href="%s">%s</a>' % (url, order_value)
    return make_square_div(label, color, order_value)


def make_square_div(label, color, order_value):
    return '<div class="square %s" title="%s">%s</div>' % (color, label, order_value)


def make_html_head():
    # Some of the code here is taken from a datatables example.
    return '''
<title>Build status page</title>
<meta http-equiv="Content-Type" content="text/html;charset=utf-8"/>

<style type="text/css" media="screen">
    @import "jquery/jquery-ui-1.9.2.custom.min.css";
    @import "jquery/jquery.dataTables_themeroller.css";
    @import "jquery/TableTools_JUI.css";

    body, div, dl, dt, dd, input, th, td { margin:0; padding:0; }
    table { border-collapse:collapse; border-spacing:0; }
    th { text-align: left }

    html, body { color: #111; font: 100%%/1.45em "Lucida Grande", Verdana, Arial, Helvetica, sans-serif; margin: 0; padding: 0; }

    a { text-decoration: none; color: #4e6ca3; }
    a:hover { text-decoration: underline; }

    ul { font-size: 80%%; list-style: none; margin: 0; padding: 0.5em; }
    li { float: left; margin-right: 1.75em; }
    li .square { width: 20px; height: 20px; font-size:100%%; text-align: center; }

    table.display thead th, table.display td { font-size: 0.8em; }
    .dataTables_info { padding-top: 0; }
    .css_right { float: right; }
    #example_wrapper .fg-toolbar { font-size: 0.8em }
    #theme_links span { float: left; padding: 2px 10px; }

    .square { border: 1px solid gray; display: inline-block; width: 15px; height: 15px; font-size: 0px; }
    .square a { display: block; }
    .pkgLatest { background: #a2d39c; }
    .pkgMissing { background: #f07878; }
    .pkgOutdated { background: #7ea7d8; }
    .pkgIgnore { background: #c8c8c8; }
    .pkgObsolete { background: #f0f078; }
    .hiddentext { font-size: 0px; }

    .sum { display: block; width: 55px; }
    .repo2 {text-align: center; }
    .repo3 {text-align: right; }

    .tooltip { position: absolute; z-index: 999; left: -9999px; border: 1px solid #111; width: 260px; }
    .tooltip p {  margin: 0; padding: 0; color: #fff; background-color: #222; padding: 2px 7px; }
</style>

<script type="text/javascript" src="jquery/jquery-1.8.3.min.js"></script>
<script type="text/javascript" src="jquery/jquery.dataTables.min.js"></script>
<script type="text/javascript" src="jquery/FixedHeader.min.js"></script>
<script type="text/javascript" src="jquery/TableTools.min.js"></script>

<script type="text/javascript" charset="utf-8">
    /* <![CDATA[ */
    function simple_tooltip(target_items, name) {
        $(target_items).each(function(i){
            $("body").append("<div class='" + name + "' id='" + name + i + "'><p>" + $(this).attr('title') + "</p></div>");
            var my_tooltip = $("#" + name + i);
            if ($(this).attr("title", "") != "") {
                $(this).removeAttr("title").mouseover(function(){
                    my_tooltip.css({opacity: 0.8, display: "none"}).fadeIn(200);
                }).mousemove(function(kmouse) {
                    my_tooltip.css({left: Math.min(kmouse.pageX + 15, $(window).width() - 260), top: kmouse.pageY + 15});
                }).mouseout(function(){
                    my_tooltip.fadeOut(200);
                });
            }
        });
    }

    $(document).ready(function() {
        var oTable = $('#csv_table').dataTable( {
            "bJQueryUI": true,
            "bPaginate": false,
            "bStateSave": true,
            "iCookieDuration": 60*60*24*7,
            "sDom": 'T<"clear">lfrtip',
            "oTableTools": {
                "aButtons": [],
                "sRowSelect": "multi"
            },
            "oLanguage": {
                "sSearch": '<span id="search" title="Special keywords to search for: diff, sync, regression, green, blue, red, yellow, gray">Search:</span>'
            }
        } );
        oTable.fnSetColumnVis(3, false);
        oTable.fnSetColumnVis(6, false);
        oTable.fnSetColumnVis(9, false);

        new FixedHeader(oTable);

        simple_tooltip("#search", "tooltip");

        // modify search to only fire after some time of no input
        var search_wait_delay = 200;
        var search_wait = 0;
        var search_wait_interval;
        $('.dataTables_filter input')
        .unbind('keypress keyup')
        .bind('keypress keyup', function(e) {
            var item = $(this);
            search_wait = 0;
            if (!search_wait_interval) search_wait_interval = setInterval(function() {
                if (search_wait >= 3){
                    clearInterval(search_wait_interval);
                    search_wait_interval = '';
                    searchTerm = $(item).val();
                    oTable.fnFilter(searchTerm);
                    search_wait = 0;
                }
                search_wait++;
            }, search_wait_delay);
        });
    } );
    /* ]]> */
</script>
'''


def make_html_legend():
    definitions = [
        ('wet', '<a href="http://ros.org/wiki/catkin">catkin</a>'),
        ('dry', '<a href="http://ros.org/wiki/rosbuild">rosbuild</a>'),
        ('<span class="square">1</span>&nbsp;<span class="square">2</span>&nbsp;<span class="square">3</span>', 'The apt repos (1) building, (2) shadow-fixed, (3) ros/public'),
        ('<span class="square pkgLatest">&nbsp;</span>', 'pkg w. same version'.replace(' ', '&nbsp;')),
        ('<span class="square pkgOutdated">&nbsp;</span>', 'pkg w. different version'.replace(' ', '&nbsp;')),
        ('<span class="square pkgMissing">&nbsp;</span>', 'pkg missing'.replace(' ', '&nbsp;')),
        ('<span class="square pkgObsolete">&nbsp;</span>', 'pkg obsolete'.replace(' ', '&nbsp;')),
        ('<span class="square pkgIgnore">&nbsp;</span>', 'pkg intentionally missing'.replace(' ', '&nbsp;'))
    ]
    definitions = ['<li><b>%s:</b>&nbsp;%s</li>' % (k, v) for (k, v) in definitions]
    return '''\
<ul>
    %s
</ul>
''' % ('\n'.join(definitions))


def make_html_table(header, footer, rows):
    '''
    Returns a string containing an HTML-formatted table, given a header and some
    rows.

    >>> make_html_table(header=['a'], rows=[[1], [2]])
    '<table>\\n<tr><th>a</th></tr>\\n<tr><td>1</td></tr>\\n<tr><td>2</td></tr>\\n</table>\\n'

    '''
    header_str = '<tr>' + ''.join('<th>%s</th>' % c for c in header) + '</tr>'
    rows_str = '\n'.join('<tr>' + ' '.join('<td>%s</td>' % c for c in r) + '</tr>' for r in rows)
    footer_str = '<tr>' + ''.join('<th>%s</th>' % ''.join(['<span class="sum repo%s">%d</span>' % (i + 1, v) for i, v in enumerate(c)]) for c in footer) + '</tr>'
    return '''\
<table class="display" id="csv_table">
    <thead>
        %s
    </thead>
    <tfoot>
        %s
    </tfoot>
    <tbody>
        %s
    </tbody>
</table>
''' % (header_str, footer_str, rows_str)


def make_html_doc(head, body):
    '''
    Returns the contents of an HTML page, given a title and body.
    '''
    return '''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="en" xml:lang="en">
    <head>
        %(head)s
    </head>
    <body>
        %(body)s
    </body>
</html>
''' % locals()
