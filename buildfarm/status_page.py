import textwrap

__all__ = ['make_status_page']

def make_status_page():
    # Load lists of wet and dry ROS package names
    #wet_pkgs = get_wet_packages()
    #dry_pkgs = get_dry_packages()

    # Load lists of packages on each distro/arch

    # Generate an in-memory table with the info to display

    # Generate HTML from the in-memory table
    header = ['package', 'version']
    rows = []
    return make_html_doc(title='Build status page',
                         body=make_html_table(header, rows))

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

