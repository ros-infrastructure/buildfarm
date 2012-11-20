import textwrap
import urllib2
import yaml

from rospkg.distro import load_distro, distro_uri

__all__ = ['make_status_page']

arches = ['amd64', 'i386']

def make_status_page():
    '''
    Returns the contents of an HTML page showing the current
    build status for all wet and dry packages on all
    supported distributions and architectures.
    '''
    # Load lists of wet and dry ROS package names
    wet_names_pkgs = get_wet_packages()
    dry_names_pkgs = get_dry_packages()

    # Load build statuses of packages on each distro/arch

    # Generate an in-memory table with the info to display

    # Generate HTML from the in-memory table
    header = ['package', 'version']
    wet_html = make_html_table_from_names_pkgs(header, wet_names_pkgs)
    dry_html = make_html_table_from_names_pkgs(header, dry_names_pkgs)
    body = '''
        <h2>Wet Packages</h2>
        %s
        <h2>Dry Packages</h2>
        %s
    ''' % (wet_html, dry_html)
    return make_html_doc(title='Build status page', body=body)

def make_html_table_from_names_pkgs(header, names_pkgs):
    rows = [(name, d.get('version')) for name, d in names_pkgs]
    rows.sort(key=lambda (pkg, version): pkg)
    return make_html_table(header, rows)

def get_wet_packages():
    '''
    Fetches a yaml file from the web and returns a list of pairs of the form

    [(short_pkg_name, pkg_dict), ...]

    for the wet (catkinized) packages.
    '''
    wet_yaml = get_wet_yaml()
    return wet_yaml['repositories'].items()

def get_wet_yaml():
    url = 'https://raw.github.com/ros/rosdistro/master/releases/groovy.yaml'
    return yaml.load(urllib2.urlopen(url))

def get_dry_packages():
    '''
    Fetches a yaml file from the web and returns a list of pairs of the form

    [(short_pkg_name, pkg_dict), ...]

    for the dry (rosbuild) packages.
    '''
    dry_yaml = get_dry_yaml()
    return [(name, d) for name, d in dry_yaml['stacks'].items() if name != '_rules']

def get_dry_yaml():
    rosdistro = 'groovy'
    return yaml.load(urllib2.urlopen(distro_uri(rosdistro)))

def make_html_doc(title, body):
    '''
    Returns the contents of an HTML page, given a title and body.
    '''
    return '''\
<html>
\t<head>
\t\t<title>%(title)s</title>
\t</head>
\t<body>
%(body)s
\t</body>
</html>
''' % locals()

def make_html_table(header, rows):
    '''
    Returns a string containing an HTML-formatted table, given a header and some
    rows.

    >>> make_html_table(header=['a'], rows=[[1], [2]])
    '<table>\\n\\t<tr><th>a</th></tr>\\n\\t<tr><td>1</td></tr>\\n\\t<tr><td>2</td></tr>\\n</table>\\n'

    '''
    header_str = '\t<tr>' + ''.join('<th>%s</th>' % c for c in header) + '</tr>'
    rows_str = '\n'.join('\t<tr>' + ''.join('<td>%s</td>' % c for c in r) + '</tr>' 
                         for r in rows)
    return '''\
<table>
%s
%s
</table>
''' % (header_str, rows_str)

def reindent(s, tab):
    lines = textwrap.dedent(s).splitlines()
    return '\n'.join(tab + l for l in lines)

def write(filename, contents):
    with open(filename, 'w') as f:
        f.write(contents)

def main():
    import BaseHTTPServer

    class Handler(BaseHTTPServer.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            page = make_status_page()
            self.wfile.write(page)

    daemon = BaseHTTPServer.HTTPServer(('', 8080), Handler)
    while True:
        daemon.handle_request()

if __name__ == '__main__':
    main()

