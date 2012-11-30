#!/usr/bin/env python

import csv
import sys


def main():
    reader = csv.reader(sys.stdin, delimiter=',', quotechar='"')
    rows = [row for row in reader]

    header = rows[0]
    rows = rows[1:]

    # move source columns before amd64/i386 columns for each distro
    column_mapping = {3: 5, 4: 3, 5: 4, 6: 8, 7: 6, 8: 7, 9: 11, 10: 9, 11: 10}
    header = [header[column_mapping[i] if column_mapping and i in column_mapping else i] for i in range(len(header))]
    rows = [[row[column_mapping[i] if column_mapping and i in column_mapping else i] for i in range(len(header))] for row in rows]

    table_name = 'csv_table'
    html_head = make_html_head(table_name)

    header = map(format_header_cell, header)
    rows = map(format_row, rows)
    body = make_html_legend()
    body += make_html_table(header, rows, table_name)

    html = make_html_doc(html_head, body)
    sys.stdout.write(html)


def format_header_cell(cell):
    replaces = {'oneiric_': 'O', 'precise_': 'P', 'quantal_': 'Q', 'amd64': '64', 'i386': '32', 'source': 'src'}
    for k, v in replaces.iteritems():
        cell = cell.replace(k, v, 1)
    return cell


def format_row(row):
    latest_version = row[1]
    row = row[:2] + [format_wet_cell(row[2])] + [format_versions_cell(c, latest_version) for c in row[3:]]
    if row[3] != row[6] or row[3] != row[9] or row[4] != row[7] or row[4] != row[10] or row[5] != row[8] or row[5] != row[11]:
        row[0] += '<span class="hiddentext"> diff</span>'
    return row


def format_wet_cell(cell):
    return 'wet' if cell == 'True' else 'dry'


def format_versions_cell(cell, latest_version):
    repos = ['building', 'shadow-fixed', 'ros/public']
    versions = cell.split('|')
    return '&nbsp;'.join([format_version(v, latest_version, r) for v, r in zip(versions, repos)])


def format_version(version, latest, repo):
    label = '%s: %s' % (repo, version)
    color = {'None': 'pkgMissing', latest: 'pkgLatest'}.get(version, 'pkgOutdated')
    # use reasonable names (even if invisible) to be searchable
    order_value = {'None': '3&nbsp;red', latest: '1&nbsp;green'}.get(version, '2&nbsp;blue')
    return square(label, color, order_value)


def square(label, color, order_value):
    return '<div class="square %s" title="%s">%s</div>' % (color, label, order_value)


def make_html_head(table_name):
    # Some of the code here is taken from a datatables example.
    return '''
<title>Build status page</title>
<meta http-equiv="Content-Type" content="text/html;charset=utf-8"/>

<style type="text/css" media="screen">
    @import "http://datatables.net/media/css/site_jui.ccss";
    @import "http://datatables.net/release-datatables/media/css/demo_table_jui.css";
    @import "http://datatables.net/media/css/jui_themes/smoothness/jquery-ui-1.7.2.custom.css";
    @import "http://datatables.net/release-datatables/extras/TableTools/media/css/TableTools.css";

    dl { font-size: 80%%; padding: 0.5em; }
    dt { float: left; font-weight: bold; text-align: right; }
    dt:after { content: ":"; }
    dd { float: left; margin: 0 1.5em 0 0.5em; }
    dl .square { width: 20px; height: 20px; font-size:100%%; text-align: center; }

    /*
     * Override styles needed due to the mix of three different CSS sources! For proper examples
     * please see the themes example in the 'Examples' section of the datatables
     * site.
     */
    .dataTables_info { padding-top: 0; }
    .css_right { float: right; }
    #example_wrapper .fg-toolbar { font-size: 0.8em }
    #theme_links span { float: left; padding: 2px 10px; }

    .square { border: 1px solid gray; display: inline-block; width: 15px; height: 15px; font-size: 0px; }
    .pkgLatest { background: #a2d39c; }
    .pkgMissing { background: #ff7878; }
    .pkgOutdated { background: #7ea7d8; }
    .hiddentext { font-size: 0px; }

    .tooltip { position: absolute; z-index: 999; left: -9999px; border: 1px solid #111; width: 260px; }
    .tooltip p {  margin: 0; padding: 0; color: #fff; background-color: #222; padding: 2px 7px; }
</style>

<script type="text/javascript" src="http://datatables.net/media/javascript/complete.min.js"></script>
<script type="text/javascript" src="http://datatables.net/release-datatables/media/js/jquery.dataTables.min.js"></script>
<script type="text/javascript" src="http://datatables.net/release-datatables/extras/FixedHeader/js/FixedHeader.min.js"></script>
<script type="text/javascript" src="http://datatables.net/release-datatables/extras/TableTools/media/js/TableTools.min.js"></script>

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
        var oTable = $('#%s').dataTable( {
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
                "sSearch": '<span id="search" title="Special keywords to search for: green, blue, red, diff">Search:</span>'
            }
        } );
        new FixedHeader(oTable);
        simple_tooltip("span#search", "tooltip");
        simple_tooltip("div.square", "tooltip");
    } );
    /* ]]> */
</script>
''' % table_name


def make_html_legend():
    definitions = [
        ('wet', '<a href="http://ros.org/wiki/catkin">catkin</a>'),
        ('dry', '<a href="http://ros.org/wiki/rosbuild">rosbuild</a>'),
        ('<span class="square">1</span>&nbsp;<span class="square">2</span>&nbsp;<span class="square">3</span>', 'The apt repos (1) building, (2) shadow-fixed, (3) ros/public'),
        ('<span class="square pkgLatest">&nbsp;</span>', 'pkg w. same version'.replace(' ', '&nbsp;')),
        ('<span class="square pkgOutdated">&nbsp;</span>', 'pkg w. different version'.replace(' ', '&nbsp;')),
        ('<span class="square pkgMissing">&nbsp;</span>', 'pkg missing'.replace(' ', '&nbsp;'))
    ]
    definitions = ['<dt>%s</dt><dd>%s</dd>' % (k, v) for (k, v) in definitions]
    return '''\
<dl>
    %s
</dl>
''' % ('\n'.join(definitions))


def make_html_table(header, rows, table_id):
    '''
    Returns a string containing an HTML-formatted table, given a header and some
    rows.

    >>> make_html_table(header=['a'], rows=[[1], [2]])
    '<table>\\n<tr><th>a</th></tr>\\n<tr><td>1</td></tr>\\n<tr><td>2</td></tr>\\n</table>\\n'

    '''
    header_str = '<tr>' + ''.join('<th>%s</th>' % c for c in header) + '</tr>'
    rows_str = '\n'.join('<tr>' + ' '.join('<td>%s</td>' % c for c in r) + '</tr>' for r in rows)
    return '''\
<table class="display" id="%s">
    <thead>
        %s
    </thead>
    <tbody>
        %s
    </tbody>
</table>
''' % (table_id, header_str, rows_str)


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


if __name__ == '__main__':
    main()
