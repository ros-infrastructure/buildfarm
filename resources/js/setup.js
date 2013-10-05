/*$('html').on('mouseover', 'tbody tr td:nth-child(n+6) a', function(e) {
  $(this).attr('title', 'foo');
});  */

window.tbody_ready = function() {
  var table = $('table');

  /* This mouseover handler wires up the tooltip and CI url in a JIT manner
   * when the mouse hovers on a version square. Critically important is that 
   * there's only instance of this handler: on the tbody. 
   * This is the "live" event pattern. */
  $('tbody', table).on('mouseover', 'tr td:nth-child(n+6) a', function(e) {
    var a = $(this);
    var repo = ''
    if (a.is("td a:nth-child(1)")) repo = repos[0];
    if (a.is("td a:nth-child(2)")) repo = repos[1];
    if (a.is("td a:nth-child(3)")) repo = repos[2];
    var ver = a.text();
    if (!ver) ver = $('td:nth-child(2)', a.closest('tr')).text();
    a.attr('title', repo + ': ' + ver);
    a.attr('href', 'http://google.ca');
  });

  var orig_header = $('thead', table);
  var header = orig_header.clone();
  header.addClass('floating');
  $('table').prepend(header);
  $('th', header).each(function() {
    $(this).append($('<div class="spacer"></div>'));
  });
  $(window).on('resize', function() {
    $('th', header).each(function(i, el) {
      $('.spacer', this).css('width', $('tr th:nth-child(' + (i+1) + ')', orig_header).width());
    });
  });
  setTimeout(function() {
  $(window).trigger('resize');
  },0);

  $(window).on('scroll', function() {
    if ($(window).scrollTop() > table.position().top) {
      // Fixed thead
      header.addClass('fixed');
      header.css('left', -Math.max(window.scrollX, 0));
    } else {
      // Floating thead
      header.removeClass('fixed');
    }
  });
};


/*j$('document').ready(function() {
  $('th', fixed_thead).each(function(i, el) {
    var spacer_div = $('<div class="spacer"></div>');
    $(this).append(spacer_div);
  });
  $("body").append(fixed_thead); 
  $(window).on('resize', function() {
    $('th', fixed_thead).each(function(i, el) {
      $('.spacer', this).css('width', $('body table:not(.fixed) thead tr th:nth-child(' + (i+1) + ')').width());
    });
  });
  $(window).trigger('resize');
});*/


/* <![CDATA[ */
    /*function simple_tooltip(target_items, name) {
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
    }*/

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
