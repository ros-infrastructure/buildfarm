#!/usr/bin/env python

from __future__ import print_function

import csv
import os
import re
from StringIO import StringIO

# Monkey-patching over some unicode bugs in empy.
import em
em.str = unicode
em.Stream.write_old = em.Stream.write
em.Stream.write = lambda self, data: em.Stream.write_old(self, data.encode('utf8'))

import numpy as np

from buildfarm.ros_distro import debianize_package_name

version_rx = re.compile(r'[0-9.-]+[0-9]')
REPOS = ['building', 'shadow-fixed', 'ros/public']


def get_resource_hashes():
    hashes = {}
    for ext in ['css', 'js']:
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', ext)
        for filename in os.listdir(path):
            if filename.endswith('.%s' % ext):
                with open(os.path.join(path, filename)) as f:
                    hashes[filename] = hash(tuple(f.read()))
    return hashes


def get_da_strs(distro_arches):
    distros = set()
    output = []
    for d, a in distro_arches:
        if d not in distros:
            output.append(d + '_source')
            distros.add(d)
        output.append(get_dist_arch_str(d, a))
    return output


def get_distro_arches(arches, rosdistro):
    if rosdistro == 'fuerte':
        from buildfarm.ros_distro_fuerte import get_target_distros
    else:
        from buildfarm.ros_distro import get_target_distros

    distros = get_target_distros(rosdistro)
    return [(d, a) for d in distros for a in arches]


def make_versions_table(rd_data, apt_data,
                        da_strs, repo_names, rosdistro):
    '''
    Returns an in-memory table with all the information that will be displayed:
    ros package names and versions followed by debian versions for each
    distro/arch.
    '''
    left_columns = [('name', object), ('repo', object), ('version', object), ('wet', object)]
    right_columns = [(da_str, object) for da_str in da_strs]
    columns = left_columns + right_columns

    distro_debian_names = [debianize_package_name(rosdistro, pkg.name) for pkg in rd_data.packages.values()]

    # prefixes of other ros distros
    prefixes = ['ros-electric-', 'ros-fuerte-', 'ros-unstable-']
    for distribution in rd_data.rosdistro_index.distributions:
        prefixes.append('ros-%s-' % distribution)
    rosdistro_prefix = 'ros-%s-' % rosdistro
    if rosdistro_prefix in prefixes:
        prefixes.remove(rosdistro_prefix)

    non_distro_debian_names = []
    for debian_name in apt_data.debian_packages:
        skip = False
        # skip packages from other ros distros
        for prefix in prefixes:
            if debian_name.startswith(prefix):
                skip = True
        if skip:
            continue
        # skip packages which are in the rosdistro
        if debian_name in distro_debian_names:
            continue
        # skip packages without prefix of this ros distro
        if not debian_name.startswith(rosdistro_prefix):
            continue
        non_distro_debian_names.append(debian_name)

    table = np.empty(len(rd_data.packages) + len(non_distro_debian_names),
                     dtype=columns)

    # add all packages coming from the distro (wet, dry, variant)
    for i, pkg_data in enumerate(rd_data.packages.values()):
        table['name'][i] = pkg_data.name
        repo_name = ''
        try:
            repo_name = rd_data.rosdistro_dist.release_packages[pkg_data.name].repository_name
        except KeyError:
            pass
        table['repo'][i] = repo_name
        table['version'][i] = pkg_data.version
        table['wet'][i] = pkg_data.type
        for da_str in da_strs:
            debian_name = debianize_package_name(rosdistro, pkg_data.name)
            versions = get_versions(apt_data, debian_name,
                                    repo_names, da_str)
            table[da_str][i] = add_version_cell(versions)

    i = len(rd_data.packages)
    for debian_name in non_distro_debian_names:
        #undebianized_pkg_name = undebianize_package_name(rosdistro, pkg_name)
        pkg_name = debian_name
        if pkg_name.startswith(rosdistro_prefix):
            pkg_name = pkg_name[len(rosdistro_prefix):]
        table['name'][i] = pkg_name
        table['repo'][i] = ''
        table['version'][i] = ''
        table['wet'][i] = 'unknown'
        all_versions = []
        for da_str in da_strs:
            versions = get_versions(apt_data, debian_name,
                                    repo_names, da_str)
            table[da_str][i] = add_version_cell(versions)
            all_versions.extend(versions)
        # if all version values are the same (or None) lets assume that is the expected version
        unique_versions = set([v for v in all_versions if v != 'None'])
        if len(unique_versions) == 1:
            table['version'][i] = unique_versions.pop()
        i += 1

    return table


def get_versions(apt_data, pkg_name, repo_names, da_str):
    versions = []
    for repo_name in repo_names:
        v = apt_data.get_version(pkg_name, repo_name, da_str)
        v = str(v)
        v = strip_version_suffix(v)
        versions.append(v)
    return versions


def add_version_cell(versions):
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


def detect_source_version(source_name, source_records):
    """
    Detect if the source package is available on the server and return
    the version, else None
    """
    source_records.restart()
    source_lookup = source_records.lookup(source_name)
    if not source_lookup:
        #print("Missed %s" % source_name)
        return None
    else:
        src_version = strip_version_suffix(source_records.version)
        #print("Source %s %s" % (source_name, src_version))
        return src_version


def get_dist_arch_str(d, a):
    return "%s_%s" % (d, a)


def render_csv(rd_data, apt_data, outfile, rosdistro,
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

    # Make an in-memory table showing the latest deb version for each package.
    t = make_versions_table(rd_data,
                            apt_data,
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
                          rosdistro, start_time, template_file, resource_path, cached_distribution=None):
    reader = csv.reader(data_source, delimiter=',', quotechar='"')
    rows = [row for row in reader]

    headers = rows[0]
    rows = rows[1:]

    metadata_columns = [None] * 4 + [metadata_builder(c) for c in headers[4:]]
    headers = [format_header_cell(headers[i], metadata_columns[i])
               for i in range(len(headers))]

    # count non-None rows per (sub-)column
    row_counts = [[]] * 4 + [[0] * 3 for _ in range(4, len(headers))]
    for row in rows:
        for i in range(4, len(row_counts)):
            versions = get_cell_versions(row[i])
            for j in range(0, len(versions)):
                if versions[j] != 'None':
                    row_counts[i][j] += 1

    def get_package_name_from_row(row):
        return row[0]
    rows = sorted(rows, key=get_package_name_from_row)
    rows = [format_row(r, metadata_columns) for r in rows]
    inject_status_and_maintainer(cached_distribution, headers, row_counts, rows)

    # div-wrap the first three cells for layout reasons. It's difficult to contrain the
    # overall dimensions of a table cell without an inner element to use as the overflow
    # container.
    for row in rows:
        for i in range(3):
            row[i] = "<div>%s</div>" % row[i]

    repos = REPOS

    resource_hashes = get_resource_hashes()

    output = StringIO()
    try:
        interpreter = em.Interpreter(output=output)
        interpreter.file(open(template_file), locals=locals())
        return output.getvalue()
    finally:
        interpreter.shutdown()


def inject_status_and_maintainer(cached_distribution, header, counts, rows):
    from catkin_pkg.package import InvalidPackage, parse_package_string
    header[4:4] = ['Status', 'Maintainer']
    counts[4:4] = [[], []]
    for row in rows:
        status_cell = ''
        maintainer_cell = '<a>?</a>'
        # Use website url if defined, otherwise default to ros wiki
        pkg_name = row[0].split(' ')[0]
        url = 'http://wiki.ros.org/%s' % pkg_name
        repo_name = row[1]
        repo_url = None
        repo_version = None
        if row[3] == 'wet' and cached_distribution:
            pkg = cached_distribution.release_packages[pkg_name]
            repo = cached_distribution.repositories[pkg.repository_name]
            status = 'unknown'
            if pkg.status is not None:
                status = pkg.status
            elif repo.status is not None:
                status = repo.status
            status_description = ''
            if pkg.status_description is not None:
                status_description = pkg.status_description
            elif repo.status_description is not None:
                status_description = repo.status_description
            status_cell = '<a class="%s"%s/>' % (status, ' title="%s"' % status_description if status_description else '')
            pkg_xml = cached_distribution.get_release_package_xml(pkg_name)
            if pkg_xml is not None:
                try:
                    pkg = parse_package_string(pkg_xml)
                    maintainer_cell = ''.join(['<a href="mailto:%s">%s</a>' % (m.email, m.name) for m in pkg.maintainers])
                    for u in pkg['urls']:
                        if u.type == 'website':
                            url = u
                            break
                except InvalidPackage:
                    maintainer_cell = '<a><b>bad package.xml</b></a>'
            if repo.source_repository:
                repo_url = repo.source_repository.url
                repo_version = repo.source_repository.version
            elif repo.doc_repository:
                repo_url = repo.doc_repository.url
                repo_version = repo.doc_repository.version
        else:
            status_cell = '<a class="unknown"/>'
        row[0] = row[0].replace(pkg_name, '<a href="%s">%s</a>' % (url, pkg_name), 1)
        if repo_url:
            if repo_url.startswith('https://github.com/') and repo_url.endswith('.git') and repo_version:
                repo_url = '%s/tree/%s' % (repo_url[:-4], repo_version)
            row[1] = '<a href="%s">%s</a>' % (repo_url, repo_name)
        row[4:4] = [status_cell, maintainer_cell]


def format_header_cell(cell, metadata):
    if metadata and 'column_label' in metadata:
        cell = metadata['column_label']
    else:
        cell = cell[0].upper() + cell[1:]
    return cell


def format_row(row, metadata_columns):
    public_changing_on_sync = [False] * 4 + \
        [is_public_changing_on_sync(c) for c in row[4:]]
    regression = [False] * 4 + \
        [is_regression(c) for c in row[4:]]
    # Flag if this is dry or a variant so as not to show sourcedebs as red
    no_source = row[3] in ['variant', 'dry']
    # ignore source columns for dry/variant when deciding of columns are homogeneous
    diff_columns = [c for i, c in enumerate(row) if i > 3 and (not no_source or i % 3 - 1)]
    has_diff_between_rosdistros = len(set(diff_columns)) > 1

    # urls for each building repository column
    metadata = [None] * 4 + [md for md in metadata_columns[4:]]
    # for unknown packages the latest version number is only a guess so don't mark missing cells
    latest_version = row[2] if row[3] != 'unknown' else None
    # only pass no_source if this is a sourcedeb entry
    row = row[:4] + [format_versions_cell(get_cell_versions(row[i]),
                                          latest_version,
                                          no_source and metadata[i]['is_source'])
                     for i in range(4, len(row))]

    hidden_texts = []
    if has_diff_between_rosdistros:
        hidden_texts.append('diff')
    if True in public_changing_on_sync:
        hidden_texts.append('sync')
    if True in regression:
        hidden_texts.append('regression')
    if len(hidden_texts) > 0:
        row[0] += ' <span class="ht">%s</span>' % ' '.join(hidden_texts)

    type_texts = {
        'wet': 'wet',
        'dry': 'dry',
        'unknown': '?',
        'variant': "var"
    }
    row[3] = type_texts[row[3]]
    return row


def is_public_changing_on_sync(cell):
    versions = get_cell_versions(cell)
    return versions[1] != versions[2]


def is_regression(cell):
    versions = get_cell_versions(cell)
    public_version = versions[-1]
    if public_version != "None":
        public_version_parts = [int(y) for x in public_version.split('.') for y in x.split('-')]
        for v in versions:
            if v == "None":
                return True
            # a downgrade of the version is considered to be a regression
            v_parts = [int(y) for x in v.split('.') for y in x.split('-')]
            if public_version_parts > v_parts:
                return True
    return False


def get_cell_versions(cell):
    return cell.split('|')


def format_versions_cell(versions, latest_version,
                         no_source=False):
    # set the latest_version to None if no package expected
    if no_source:
        latest_version = None
    cell = ''.join([format_version(v, latest_version) for v in versions])

    return cell


def format_version(version, latest):
    if latest:
        if not version or version == 'None':
            color = 'm'  # missing
        elif version == latest:
            color = None  # latest
        else:
            color = 'o'  # outdated
    else:
        if not version or version == 'None':
            color = 'i'  # ignore
        else:
            color = 'obs'  # obsolete

    label = version
    if version == latest:
        # When version is the same as latest, Javascript will infer it. This
        # avoids repetition in the HTML page.
        label = None
    if color in ['m', 'i']:
        # These color blocks represent no-package, which Javascript knows too;
        # no need to explicitly specify.
        label = None
    return make_square_div(label, color)


def make_square_div(label, color):
    if color:
        if label:
            return '<a class="%s">%s</a>' % (color, label)
        else:
            return '<a class="%s"/>' % color
    else:
        return '<a/>'
