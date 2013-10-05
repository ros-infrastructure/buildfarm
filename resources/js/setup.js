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

    /*$(document).ready(function() {
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
                %s
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

        // query via url
        var url_vars = {};
        window.location.href.replace(/[?&]+([^=&]+)=([^&]*)/gi, function(m, key, value) {
            url_vars[key] = value;
        });
        if ('q' in url_vars) {
            oTable.fnFilter(url_vars['q'])
        }
    }* ); */
