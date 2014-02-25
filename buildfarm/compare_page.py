#!/usr/bin/env python

from __future__ import print_function

from distutils.version import LooseVersion
import itertools
from StringIO import StringIO

# Monkey-patching over some unicode bugs in empy.
import em
em.str = unicode
em.Stream.write_old = em.Stream.write
em.Stream.write = lambda self, data: em.Stream.write_old(self, data.encode('utf8'))

from rosdistro import get_cached_distribution


def generate_html(index, distro_names, start_time, template_file, resource_path):
    headers = ['Repo', 'Maintainer'] + [d[0].upper() + d[1:].lower() for d in distro_names]
    distros = [get_cached_distribution(index, d) for d in distro_names]
    repos = {}

    repo_names = [d.repositories.keys() for d in distros]
    repo_names = [x for y in repo_names for x in y]

    for repo_name in repo_names:
        row = format_row(repo_name, distros)
        if row:
            repos[repo_name] = row

    rows = []
    for repo_name in sorted(repos.keys()):
        rows.append(repos[repo_name])
    repos = repos.keys()

    output = StringIO()
    try:
        interpreter = em.Interpreter(output=output)
        interpreter.file(open(template_file), locals=locals())
        return output.getvalue()
    finally:
        interpreter.shutdown()


class Row(object):

    def __init__(self, repo_name):
        self.repo_name = repo_name
        self.repo_urls = []
        self.maintainers = {}
        self.versions = []
        self.branches = []

    def get_repo_name_with_link(self):
        valid_urls = [u for u in self.repo_urls if u]
        if len(set(valid_urls)) == 1:
            return '<a href="%s">%s</a>' % (valid_urls[0], self.repo_name)

        unique_urls = []
        [unique_urls.append(u) for u in valid_urls if u not in unique_urls]
        parts = [self.repo_name]
        for i, repo_url in enumerate(unique_urls):
            parts.append(' [<a href="%s">%d</a>]' % (repo_url, i + 1))
        return ' '.join(parts)

    def get_maintainers(self):
        return ' '.join([self.maintainers[k] for k in sorted(self.maintainers.keys())])

    def get_labels(self, distros):
        all_versions = [LooseVersion(v) if v else v for v in self.versions]
        valid_versions = [v for v in all_versions if v]
        labels = []
        if any([_is_only_patch_is_different(p[0], p[1]) for p in itertools.combinations(valid_versions, 2)]):
            labels.append('diff_patch')
        if any([_is_greater(p[0], p[1]) for p in itertools.combinations(valid_versions, 2)]):
            labels.append('downgrade_version')

        versions_and_branches = zip(itertools.combinations(all_versions, 2), itertools.combinations(self.branches, 2))
        if any([_is_same_version_but_different_branch(vb[0][0], vb[0][1], vb[1][0], vb[1][1]) for vb in versions_and_branches]):
            labels.append('diff_branch_same_version')
        return labels

def _is_only_patch_is_different(a, b):
    return a.version[0] == b.version[0] and a.version[1] == b.version[1] and a.version[2] != b.version[2]

def _is_greater(a, b):
    return a.version[0] > b.version[0] or (a.version[0] == b.version[0] and a.version[1] > b.version[1])

def _is_same_version_but_different_branch(version_a, version_b, branch_a, branch_b):
    # skip when any version is unknown
    if not version_a or not version_b:
        return False
    # skip when any branch is unknown or they are equal
    if not branch_a or not branch_b or branch_a == branch_b:
        return False
    return version_a.version[0] == version_b.version[0] and version_a.version[1] == version_b.version[1]


def format_row(repo_name, distros):
    from catkin_pkg.package import InvalidPackage, parse_package_string
    row = Row(repo_name)
    for distro in distros:
        repo_url = None
        version = None
        branch = None
        if repo_name in distro.repositories:
            repo = distro.repositories[repo_name]

            rel_repo = repo.release_repository
            if rel_repo:
                version = rel_repo.version
                for pkg_name in rel_repo.package_names:
                    pkg_xml = distro.get_release_package_xml(pkg_name)
                    if pkg_xml is not None:
                        try:
                            pkg = parse_package_string(pkg_xml)
                            for m in pkg.maintainers:
                                row.maintainers[m.name] = '<a href="mailto:%s">%s</a>' % (m.email, m.name)
                        except InvalidPackage:
                            row.maintainers['zzz'] = '<b>invalid package.xml in %s</b>' % distro.name

                    if repo.source_repository:
                        repo_url = repo.source_repository.url
                    elif repo.doc_repository:
                        repo_url = repo.doc_repository.url

            source_repo = repo.source_repository
            if source_repo:
                branch = source_repo.version
            else:
                doc_repo = repo.source_repository
                if doc_repo:
                    branch = doc_repo.version

        row.repo_urls.append(repo_url)
        row.versions.append(version)
        row.branches.append(branch)

    # skip if no versions available
    if not [v for v in row.versions if v]:
        return None

    data = [row.get_repo_name_with_link(), row.get_maintainers()] + [v if v else '' for v in row.versions]

    labels = row.get_labels(distros)
    if len(labels) > 0:
        data[0] += ' <span class="ht">%s</span>' % ' '.join(labels)

    # div-wrap all cells for layout reasons
    for i, value in enumerate(data):
        data[i] = '<div>%s</div>' % value

    return data
