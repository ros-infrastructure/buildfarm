var SORT_COLUMNS = [ 1, 2, 3, 4, 5 ];

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
    if (repo == repos[0]) {
      // TODO: Actually build up this URL properly.
      a.attr('href', 'http://jenkins.ros.org/view/HbinR32/job/ros-hydro-actionlib_binarydeb_raring_i386/');
    }
  });

  /* CSS makes the original header in the document invisible. We create a clone of that 
   * to be the "real" header, with the dimensions copied to the clone, and the clone alternatiing
   * between being position: absolute and position: fixed, depending on the scroll of the page. */ 
  var orig_header = $('thead', table);
  var header = orig_header.clone();
  header.addClass('floating').hide();
  $('table').prepend(header);
  // Insert spacer divs into the floating header to that it matches the
  // dimensions of the original table.
  $('th', header).each(function() {
    $(this).append($('<div class="spacer"></div>'));
  });
  $(window).on('resize', function() {
    // Resize the spacers to make the floating version match the original.
    $('th', header).each(function(i, el) {
      $('.spacer', this).css('width', $('tr th:nth-child(' + (i+1) + ')', orig_header).width());
    });
    header.show();
  });
  setTimeout(function() {
    $(window).trigger('resize');
  }, 0);

  var last_left = null;
  $(window).on('scroll', function() {
    if ($(window).scrollTop() > table.position().top) {
      // Fixed thead
      header.addClass('fixed');
      var left = window.scrollX;
      left = Math.max(left, 0);
      left = Math.min(left, table.width() - document.documentElement.clientWidth);
      if (left != last_left) {
        header.css('left', -left);
        last_left = left;
      }
    } else {
      // Floating thead
      header.removeClass('fixed');
    }
  });

  /* If there is a load-time query string which will trigger an immediate
   * filter, hide the in-progress loading of the table. Deliberately do this
   * after the header cloning dingus above, so that the header dimensions are
   * correct. */
  if (window.queries || window.sort) {
    $('tbody').css('visibility', 'hidden');
    setTimeout(function() {
      $('tbody').css('visibility', 'visible').hide();
    }, 0);
  }
};

window.body_ready = function() {
  var url_parts = window.location.href.split('?');
  if (url_parts[1]) {
    var query_parts = url_parts[1].split('&');
    $.each(query_parts, function(i, query_part) {
      key_val = query_part.split('=');
      switch(key_val[0]) {
        case 'q': window.queries = key_val[1]; break;
        case 's': window.sort = key_val[1]; break;
        case 'r': window.reverse = key_val[1]; break;
      }
    });
  }
};

window.body_done = function() {
  if (window.queries || window.sort) {
    filter_table();
    $('tbody').show();
  }
}

function scan_rows() {
  window.rows = [];
  $('table tbody tr').each(function() {
    row_info = [$(this).html()];
    var tr = this;
    $.each(SORT_COLUMNS, function() {
      var sort_text = $("td:nth-child(" + this + ")", tr).text();
      row_info.push(sort_text);
    });
    window.rows.push(row_info);
  });
  console.log("Total rows found: " + window.rows.length);
}

function filter_table() {
  // One time setup, to build up the array of row contents combined with sortable fields.
  if (!window.rows) { scan_rows(); }

  // If query provided, copy only the matching rows to the result set.
  // It not, just use the original. It gets mangled when sorting, but that's okay.
  var result_rows;
  if (window.queries) {
    var queries = window.queries.split("+");
    console.log("Filtering for queries:", queries);
    result_rows = $.map(window.rows, function(row) {
      for (var i = 0; i < queries.length; i++) {
        if (row[0].indexOf(queries[i]) == -1) return null;
      }
      return [row];
    });
  } else {
    result_rows = window.rows;
  }

  if (window.sort) {
    var sort = parseInt(window.sort);
    var order = 1;
    if (window.reverse == 1) order = -1;
    result_rows.sort(function(a, b) {
      if (a[sort] > b[sort]) return order;
      if (a[sort] < b[sort]) return -order;
      return 0;
    });
  }

  var result_rows_plain = $.map(result_rows, function(row) { return row[0]; });
  $('table tbody').html("<tr/><tr>" + result_rows_plain.join("</tr><tr>") + "</tr>");
}

