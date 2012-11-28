#!/usr/bin/env python

import csv
import sys
from xml.dom import minidom

def main():
    r = csv.reader(sys.stdin, delimiter=',', quotechar='"')
    rows = [row for row in r]
    table_name = 'csv_table'
    html_head = make_html_head(table_name)
    body = make_html_table(rows[0], rows[1:], table_name)
    html = make_html_doc(html_head, body)
    html = prettify_html(html)
    sys.stdout.write(html)

def prettify_html(html):
    dom = minidom.parseString(html)
    return dom.toprettyxml()

def make_html_head(table_name):
    return '''
<title>Build status page</title>
<script src="http://ajax.aspnetcdn.com/ajax/jquery/jquery-1.8.0.js" type="text/javascript"></script>
<script src="http://ajax.aspnetcdn.com/ajax/jquery.ui/1.8.18/jquery-ui.min.js" type="text/javascript"></script>
<script src="http://ajax.aspnetcdn.com/ajax/jquery.dataTables/1.9.4/jquery.dataTables.min.js" type="text/javascript"></script>
<script type="text/javascript" charset="utf-8">
    $(document).ready(function() {
        $('#%s').dataTable();
    } );
</script>
''' % table_name

def make_html_doc(head, body):
    '''
    Returns the contents of an HTML page, given a title and body.
    '''
    return '''\
<html>
    <head>
        %(head)s
    </head>
    <body>
        %(body)s
    </body>
</html>
''' % locals()

def make_html_table(header, rows, id):
    '''
    Returns a string containing an HTML-formatted table, given a header and some
    rows.

    >>> make_html_table(header=['a'], rows=[[1], [2]])
    '<table>\\n<tr><th>a</th></tr>\\n<tr><td>1</td></tr>\\n<tr><td>2</td></tr>\\n</table>\\n'

    '''
    header_str = '<tr>' + ''.join('<th>%s</th>' % c for c in header) + '</tr>'
    rows_str = '\n'.join('<tr>' + ''.join('<td>%s</td>' % c for c in r) + '</tr>' 
                         for r in rows)
    return '''\
<table class="display" id="%s">
    <thead>
        %s
    </thead>
    <tbody>
        %s
    </tbody>
</table>
''' % (id, header_str, rows_str)

if __name__ == '__main__':
    main()

