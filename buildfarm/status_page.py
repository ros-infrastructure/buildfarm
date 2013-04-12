#!/usr/bin/env python

from __future__ import print_function

import csv
import os
import logging
import re
import time
import urllib2
import yaml

import apt
import apt_pkg
import numpy as np

import buildfarm.apt_root
from buildfarm.ros_distro import debianize_package_name,\
    undebianize_package_name
from rospkg.distro import distro_uri

version_rx = re.compile(r'[0-9.-]+[0-9]')


class PackageVersion(object):
    """
    A class to store package versions.
    """
    def __init__(self, name, rosdistro):
        self._name = name
        self.debian_name = debianize_package_name(rosdistro, name)
        self._versions = {}

    def add_version(self, repo, distro_arch, version_string):
        self._versions[(repo, distro_arch)] = version_string

    def get_version(self, repo, distro_arch):
        if (repo, distro_arch) in self._versions:
            return self._versions[(repo, distro_arch)]
        else:
            return None

    def _pp_struct_(self):
        return {'name': self._name,
                'debian_name': self.debian_name,
                'versions': self._versions}


class VersionCache(object):
    def __init__(self, rosdistro):
        self._cache = {}
        self._rosdistro = rosdistro
        self._bootstrap_from_rosdistro(rosdistro)
        self._primary_arch = None  # fill with the first used arch

    def add(self, name, repo, distro_arch, version_string):
        if name not in self._cache:
            self._cache[name] = PackageVersion(name, self._rosdistro)
        self._cache[name].add_version(repo, distro_arch, version_string)

    def get_version(self, name, repo, distro_arch):
        if not name in self._cache:
            return None
        return self._cache[name].get_version(repo, distro_arch)

    def list_debian_names(self):
        return [p.debian_name for p in self._cache.values()]

    def pprint(self):
        import pprint
        pp = pprint.PrettyPrinter()
        for k, v in self._cache.items():
            print("%s:" % (k))
            pp.pprint(v._pp_struct_())

    def _bootstrap_from_rosdistro(self, rosdistro):
        if rosdistro == 'fuerte':
            from buildfarm.ros_distro_fuerte import Rosdistro
        else:
            from buildfarm.ros_distro import Rosdistro
        rd = Rosdistro(rosdistro)
        for name in rd.get_package_list():
            self.add(name, 'rosdistro', 'wet',
                     rd.get_version(name, full_version=True))
        if rosdistro not in ['fuerte', 'groovy', 'hydro', 'indigo']:
            return
        dry_yaml = yaml.load(urllib2.urlopen(distro_uri(rosdistro)))
        for name, d in dry_yaml['stacks'].items():
            if name == '_rules':
                continue
            self.add(name, 'rosdistro', 'dry', d.get('version'))
        for variant in dry_yaml['variants']:
            if len(variant) != 1:
                logging.warn("Not length 1 dict in variant %s: skipping" % \
                                 variant)
                continue
            name = variant.keys()[0]
            self.add(name, 'rosdistro', 'variant', '1.0.0')

    def fill_debian_versions(self, rootdir, repo, distro, arch):
        """
        Call this after populating the rosdistro names, and it will
        try to fill in the debian versions.
        """
        distro_arch = "%s_%s" % (distro, arch)
        if not self._primary_arch:
            self._primary_arch = arch

        logging.debug("building Cache")
        aptcache = get_apt_cache(get_repo_cache_dir_name(rootdir,
                                                         repo,
                                                         distro_arch))
        logging.debug("iterating cache length %d" % len(self._cache))
        for p in self._cache.values():
            if p.debian_name in aptcache:
                apt_p = aptcache[p.debian_name]
                version_obj = getattr(apt_p, 'candidate', None)
                version = getattr(version_obj, 'version', None)
                self.add(p._name, repo, distro_arch, version)
                # only detect source for one arch
                if self._primary_arch == arch:
                    self.add(p._name, repo, distro + "_source",
                             detect_source_version(version_obj))

    def get_distro_versions(self):
        """
        Return the list of rosdistro versions and distro type (dry, wet)
        return np.array( ( name, version, wet == True), ... ])
        """
        output = []
        for p in self._cache.values():
            version = p.get_version('rosdistro', 'wet')
            if version:
                output.append((p._name, version, 'wet'))
            version = p.get_version('rosdistro', 'variant')
            if version:
                output.append((p._name, version, 'variant'))
            version = p.get_version('rosdistro', 'dry')
            if version:
                output.append((p._name, version, 'dry'))
        return np.array(output)


def get_repo_da_caches(rootdir, ros_repo_names, da_strs):
    '''
    Returns [(repo_name, da_str, cache_dir), ...]

    For example, get_repo_da_caches('/tmp/ros_apt_caches', \
                   ['ros', 'shadow-fixed'], ['quantal_i386'])
    '''
    return [(ros_repo_name, da_str,
             get_repo_cache_dir_name(rootdir, ros_repo_name, da_str))
            for ros_repo_name in ros_repo_names
            for da_str in da_strs]


def get_apt_cache(dirname):
    c = apt.Cache(rootdir=dirname)
    c.open()
    return c


def get_ros_repo_names(ros_repos):
    return ros_repos.keys()


def get_da_strs(distro_arches):
    distros = set([d for d, a in distro_arches])
    return [d + '_source' for d in distros] +\
        [get_dist_arch_str(d, a) for d, a in distro_arches]


def get_distro_arches(arches, rosdistro):
    if rosdistro == 'fuerte':
        from buildfarm.ros_distro_fuerte import get_target_distros
    else:
        from buildfarm.ros_distro import get_target_distros

    distros = get_target_distros(rosdistro)
    return [(d, a) for d in distros for a in arches]


def make_versions_table(version_cache, ros_pkgs_table, repo_name_da_to_pkgs,
                        da_strs, repo_names, rosdistro):
    '''
    Returns an in-memory table with all the information that will be displayed:
    ros package names and versions followed by debian versions for each
    distro/arch.
    '''
    left_columns = [('name', object), ('version', object), ('wet', object)]
    right_columns = [(da_str, object) for da_str in da_strs]
    columns = left_columns + right_columns

    debian_names = version_cache.list_debian_names()

    non_ros_pkg_names = set([])
    ros_pkg_names = set(debian_names)
    for pkgs in repo_name_da_to_pkgs.values():
        pkg_names = set([pkg.name for pkg in pkgs])
        non_ros_pkg_names |= pkg_names - ros_pkg_names

    table = np.empty(len(ros_pkgs_table) + len(non_ros_pkg_names),
                     dtype=columns)

    for i, (name, version, wet) in enumerate(ros_pkgs_table):
        table['name'][i] = name
        table['version'][i] = version
        table['wet'][i] = wet
        for da_str in da_strs:
            table[da_str][i] = add_version_cell(version_cache,
                                                name,
                                                repo_names,
                                                da_str)

    i = len(ros_pkgs_table)
    for pkg_name in non_ros_pkg_names:
        undebianized_pkg_name = undebianize_package_name(rosdistro, pkg_name)
        table['name'][i] = undebianized_pkg_name
        table['version'][i] = ''
        table['wet'][i] = 'unknown'
        for da_str in da_strs:
            table[da_str][i] = add_version_cell(version_cache,
                                                undebianized_pkg_name,
                                                repo_names, da_str)
        i += 1

    return table


def add_version_cell(version_cache, pkg_name, repo_names, da_str):
    versions = []
    for repo_name in repo_names:
        v = version_cache.get_version(pkg_name, repo_name, da_str)
        v = str(v)
        v = strip_version_suffix(v)
        versions.append(v)
    return '|'.join(versions)


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


def detect_source_version(version_obj):
    """
    Detect if the source package is available on the server and return
    the version, else None
    """
    src = apt_pkg.SourceRecords()
    source_name = version_obj.source_name
    source_version = version_obj._records.source_ver or \
        version_obj.source_version
    source_lookup = src.lookup(source_name)

    while source_lookup and src.version not in source_version:
        source_lookup = src.lookup(source_name)
    if source_lookup:
        return src.version
    return None


def get_dist_arch_str(d, a):
    return "%s_%s" % (d, a)


def get_repo_cache_dir_name(rootdir, ros_repo_name, dist_arch):
    return os.path.join(rootdir, ros_repo_name, dist_arch)


def build_repo_cache(dir_, ros_repo_name, ros_repo_url,
                     distro, arch, update=True):
    logging.debug('Setting up an apt directory at %s', dir_)
    repo_dict = {ros_repo_name: ros_repo_url}
    buildfarm.apt_root.setup_apt_rootdir(dir_, distro, arch,
                                         additional_repos=repo_dict)
    logging.info('Getting a list of packages for %s-%s', distro, arch)
    cache = apt.Cache(rootdir=dir_)
    cache.open()
    if update:
        cache.update()
        # Have to open the cache again after updating.
        cache.open()


def get_pkgs_from_apt_cache(cache_dir, substring):
    cache = apt.Cache(rootdir=cache_dir)
    cache.open()
    return [cache[name] for name in cache.keys() if name.startswith(substring)]


def build_version_cache(rootdir, rosdistro, distro_arches,
                        ros_repos, update=True):
    version_cache = VersionCache(rosdistro)
    for repo in ros_repos:
        for (d, a) in distro_arches:
            da_str = "%s_%s" % (d, a)
            build_repo_cache(get_repo_cache_dir_name(rootdir,
                                                     d, a),
                             repo,
                             ros_repos[repo],
                             d, a, update)
            logging.debug("Filling debian version for %s %s", repo, da_str)
            version_cache.fill_debian_versions(rootdir, repo, d, a)

    return version_cache


def render_csv(version_cache, rootdir, outfile, rosdistro,
               distro_arches, ros_repos):
    distros = {}

    for (d, a) in distro_arches:
        if not d in distros:
            distros[d] = []
        distros[d].append(a)
    das = []
    for d in distros:
        for a in distros[d]:
            das.append((d, a))
    da_strs = get_da_strs(das)
    ros_repo_names = get_ros_repo_names(ros_repos)
    repo_da_caches = get_repo_da_caches(rootdir, ros_repo_names, da_strs)

    ros_pkgs_table = version_cache.get_distro_versions()

    # Get the version of each Debian package in each ROS apt repository.
    repo_name_da_to_pkgs = dict(((repo_name, da_str),
                                 get_pkgs_from_apt_cache(cache, 'ros-%s-' % \
                                                             rosdistro))
                                for repo_name, da_str, cache in repo_da_caches)

    # Make an in-memory table showing the latest deb version for each package.
    t = make_versions_table(version_cache,
                            ros_pkgs_table,
                            repo_name_da_to_pkgs,
                            da_strs,
                            ros_repos.keys(),
                            rosdistro)

    with open(outfile, 'w') as fh:
        # Output CSV from the in-memory table
        w = csv.writer(fh)
        w.writerow(t.dtype.names)
        for row in t:
            w.writerow(row)


def transform_csv_to_html(data_source, metadata_builder,
                          rosdistro, start_time):
    reader = csv.reader(data_source, delimiter=',', quotechar='"')
    rows = [row for row in reader]

    header = rows[0]
    rows = rows[1:]

    html_head = make_html_head(rosdistro, start_time)

    metadata_columns = [None] * 3 + [metadata_builder(c) for c in header[3:]]
    header = [format_header_cell(header[i],
                                 metadata_columns[i]) \
                  for i in range(len(header))]

    # count non-None rows per (sub-)column
    counts = [[]] * 3 + [[0] * 3 for _ in range(3, len(header))]
    for row in rows:
        for i in range(3, len(counts)):
            versions = get_cell_versions(row[i])
            for j in range(0, len(versions)):
                if versions[j] != 'None':
                    counts[i][j] += 1

    rows = [format_row(r, metadata_columns) for r in rows]
    body = make_html_legend()
    body += make_html_table(header, counts, rows)

    return make_html_doc(html_head, body)


def format_header_cell(cell, metadata):
    if metadata and 'column_label' in metadata:
        cell = metadata['column_label']
    else:
        cell = cell[0].upper() + cell[1:]
    return cell


def format_row(row, metadata_columns):
    latest_version = row[1]
    public_changing_on_sync = [False] * 3 + \
        [is_public_changing_on_sync(c) for c in row[3:]]
    # as long as the status page is generated on lucid it does not
    # handle source repos correctly which therefore need to be skipped
    row_without_sources = [c for i, c in enumerate(row) if i > 2 and i % 3]
    has_diff_between_rosdistros = len(set(row_without_sources)) > 1

    # urls for each building repository column
    metadata = [None] * 3 + [md for md in metadata_columns[3:]]
    if row[2] == 'variant':
        metadata = [None for _ in range(len(metadata))]
    job_urls = [md['job_url'].format(pkg=row[0].replace('_', '-')) \
                    if md else None for md in metadata]

    row = row[:3] + [format_versions_cell(row[i],
                                          latest_version,
                                          job_urls[i],
                                          public_changing_on_sync[i]) \
                         for i in range(3, len(row))]
    if has_diff_between_rosdistros:
        row[0] += ' <span class="hiddentext">diff</span>'

    return row


def is_public_changing_on_sync(cell):
    versions = get_cell_versions(cell)
    return versions[1] != versions[2]


def get_cell_versions(cell):
    return cell.split('|')


def format_versions_cell(cell, latest_version, url=None,
                         public_changing_on_sync=False):
    versions = get_cell_versions(cell)
    repos = ['building', 'shadow-fixed', 'ros/public']
    search_suffixes = ['1', '2', '3']
    cell = ''.join([format_version(v,
                                   latest_version,
                                   r,
                                   s,
                                   versions[-1],
                                   url if r == 'building' else None)\
                        for v, r, s in zip(versions, repos, search_suffixes)])

    if public_changing_on_sync:
        cell += '<span class="hiddentext">sync</span>'

    return cell


def format_version(version, latest, repo, search_suffix,
                   public_version, url=None):
    label = '%s: %s' % (repo, version)
    if latest:
        color = {'None': 'pkgMissing',
                 latest: 'pkgLatest'}.get(version, 'pkgOutdated')
        # use reasonable names (even if invisible) to be searchable
        order_value = {'None': '5&nbsp;red',
                       latest: '1&nbsp;green'}.get(version, '3&nbsp;blue')
    else:
        color = {'None': 'pkgIgnore'}.get(version, 'pkgObsolete')
        # use reasonable names (even if invisible) to be searchable
        order_value = {'None': '2&nbsp;gray'}.get(version, '4&nbsp;yellow')
    order_value += search_suffix
    if repo != 'ros/public' and is_regression(version, public_version):
        order_value += '&nbsp;regression' + search_suffix
    if url:
        order_value = '<a href="%s">%s</a>' % (url, order_value)
    return make_square_div(label, color, order_value)


def is_regression(version, public_version):
    # public has a package and specific repo doesn't
    return public_version != 'None' and version == 'None'


def make_square_div(label, color, order_value):
    return '<div class="square %s" title="%s">%s</div>' % \
        (color, label, order_value)


def make_html_head(rosdistro, start_time):
    rosdistro = rosdistro[0].upper() + rosdistro[1:]
    # Some of the code here is taken from a datatables example.
    return '''
<title>ROS %s - build status page - %s</title>
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

    .square { border: 1px solid gray; display: inline-block; font-size: 0px; height: 15px; margin-right: 4px; width: 15px; }
    .square a { display: block; }
    .pkgLatest { background: #a2d39c; }
    .pkgMissing { background: #f07878; }
    .pkgOutdated { background: #7ea7d8; }
    .pkgIgnore { background: #c8c8c8; }
    .pkgObsolete { background: #f0f078; }
    .hiddentext { color: transparent; font-size: 0px; }

    table.dataTable thead th div.DataTables_sort_wrapper span.sum { position: inherit; }
    table.DTTT_selectable tbody tr { cursor: inherit; }
    .sum { display: block; font-size: 0.8em; width: 55px; }
    .repo2 {text-align: center; }
    .repo3 {text-align: right; }
    .filter_column input { width: 55px; }
    th:first-child .filter_column input { width: 150px; }
    .search_init { color: gray; }

    .tooltip { position: absolute; z-index: 999; left: -9999px; border: 1px solid #111; width: 260px; }
    .tooltip p {  margin: 0; padding: 0; color: #fff; background-color: #222; padding: 2px 7px; }
</style>

<script type="text/javascript" src="jquery/jquery-1.8.3.min.js"></script>
<script type="text/javascript" src="jquery/jquery.dataTables.min.js"></script>
<script type="text/javascript" src="jquery/jquery.dataTables.columnFilter.js"></script>
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
        oTable.columnFilter( {
            "aoColumns": [
                { type: "text" },
                { type: "text" },
                { type: "select",  values: ['wet', 'dry', 'variant', 'unknown'] },
                { type: "text" },
                { type: "text" },
                { type: "text" },
                { type: "text" },
                { type: "text" },
                { type: "text" },
                { type: "text" },
                { type: "text" },
                { type: "text" }
            ],
            "bUseColVis": true
        } );

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
''' % (rosdistro, time.strftime('%Y-%m-%d %H:%M:%S %Z', start_time))


def make_html_legend():
    definitions = [
        ('wet', '<a href="http://ros.org/wiki/catkin">catkin</a>'),
        ('dry', '<a href="http://ros.org/wiki/rosbuild">rosbuild</a>'),
        ('<span class="square">1</span>&nbsp;<span class="square">2</span>&nbsp;<span class="square">3</span>', 'The apt repos (1) building, (2) shadow-fixed, (3) ros/public'),
        ('<span class="square pkgLatest">&nbsp;</span>', 'same version'.replace(' ', '&nbsp;')),
        ('<span class="square pkgOutdated">&nbsp;</span>', 'different version'.replace(' ', '&nbsp;')),
        ('<span class="square pkgMissing">&nbsp;</span>', 'missing'.replace(' ', '&nbsp;')),
        ('<span class="square pkgObsolete">&nbsp;</span>', 'obsolete'.replace(' ', '&nbsp;')),
        ('<span class="square pkgIgnore">&nbsp;</span>', 'intentionally missing'.replace(' ', '&nbsp;'))
    ]
    definitions = ['<li><b>%s:</b>&nbsp;%s</li>' % (k, v) for (k, v) in definitions]
    return '''\
<ul>
    %s
</ul>
''' % ('\n'.join(definitions))


def make_html_table(columns, counts, rows):
    '''
    Returns a string containing an HTML-formatted table, given a header and some
    rows.

    >>> make_html_table(header=['a'], rows=[[1], [2]])
    '<table>\\n<tr><th>a</th></tr>\\n<tr><td>1</td></tr>\\n<tr><td>2</td></tr>\\n</table>\\n'

    '''
    headers = []
    for i in range(len(columns)):
        headers.append('%s<br/>%s' % (columns[i], ''.join(['<span class="sum repo%s">%d</span>' % (i + 1, v) for i, v in enumerate(counts[i])])))
    header_str = '<tr>' + ''.join('<th>%s</th>' % c for c in headers) + '</tr>'
    rows_str = '\n'.join('<tr>' + ' '.join('<td>%s</td>' % c for c in r) + '</tr>' for r in rows)
    footer_str = '<tr>' + ''.join('<th>%s</th>' % (c if i != 2 else '') for i, c in enumerate(columns)) + '</tr>'
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
