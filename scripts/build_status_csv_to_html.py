#!/usr/bin/env python

import csv
import sys

def main():
    reader = csv.reader(sys.stdin, delimiter=',', quotechar='"')
    rows = [row for row in reader]
    table_name = 'csv_table'
    html_head = make_html_head(table_name)
    header = rows[0]
    rest = map(format_row, rows[1:])
    body = make_html_table(header, rest, table_name)
    html = make_html_doc(html_head, body)
    sys.stdout.write(html)

def format_row(row):
    latest_version = row[1]
    return row[:3] + [format_versions_cell(c, latest_version) for c in row[3:]]

def format_versions_cell(cell, latest_version):
    repos = ['building', 'shadow-fixed', 'ros/public']
    versions = cell.split('|')
    return ' '.join([format_version(v, latest_version, r) for v, r in zip(versions, repos)])

def format_version(version, latest, repo):
    color = {'None': 'red', latest: 'green'}.get(version, 'blue')
    label = '%s: %s' % (repo, version)
    return tooltip_square(label, color)

def tooltip_square(label, color):
    return '<div class="%s square" title="%s" /> </div>' % (color, label)

def make_html_head(table_name):
    # Some of the code here is taken from a datatables example.
    return '''
<title>Build status page</title>

<style type="text/css" media="screen">
    @import "http://datatables.net/media/css/site_jui.ccss";
    @import "http://datatables.net/release-datatables/media/css/demo_table_jui.css";
    @import "http://datatables.net/media/css/jui_themes/smoothness/jquery-ui-1.7.2.custom.css";
    
    /*
     * Override styles needed due to the mix of three different CSS sources! For proper examples
     * please see the themes example in the 'Examples' section of the datatables
     * site.
     */
    .dataTables_info { padding-top: 0; }
    .dataTables_paginate { padding-top: 0; }
    .css_right { float: right; }
    #example_wrapper .fg-toolbar { font-size: 0.8em }
    #theme_links span { float: left; padding: 2px 10px; }

    .red { background:#ff7878; }
    .green { background:#a2d39c; }
    .blue { background:#7ea7d8; }
    .square { width:10px; height:10px; }
    div.square { display:inline-block; }
</style>

<script type="text/javascript" src="http://datatables.net/media/javascript/complete.min.js"></script>
<script type="text/javascript" src="http://datatables.net/release-datatables/media/js/jquery.dataTables.min.js"></script>

<script type="text/javascript" charset="utf-8">
    $(document).ready(function() {
        $('#%s').dataTable( {
            "bJQueryUI": true,
            "sPaginationType": "full_numbers"
        } );
    } );
</script>
''' % table_name

def make_html_doc(head, body):
    '''
    Returns the contents of an HTML page, given a title and body.
    '''
    return '''\
<!DOCTYPE html>
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

