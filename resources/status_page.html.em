@{import time}
<!DOCTYPE html>
<html>
<head>
  <title>ROS @(rosdistro.capitalize()) - build status page - @(time.strftime('%Y-%m-%d %H:%M:%S %Z', start_time))</title>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8"/>

  <script type="text/javascript" src="js/zepto.min.js"></script>
  <script type="text/javascript">
    window.repos = @(repr(repos));
  </script>
  <script type="text/javascript" src="js/setup.js"></script>

  <link rel="stylesheet" href="css/status_page.css" />
</head>
<body>
  <dl>
@[for term, defn in legend]@
    <dt>@(term)</dt><dd>@(defn)</dd>
@[end for]@
  </dl>
  <table>
    <thead>
       <tr>
@[for header, row_count in zip(headers, row_counts)]@
      <th><div>@(header)</div>@[for count in row_count]<span class="sum">@(count)</span>@[end for]</th>
@[end for]@
      </tr>    
    </thead>
    <tfoot>
      <tr>
@[for header in headers]@
      <th>@(header)</th>
@[end for]@
      </tr>
    </tfoot>
    <tbody>
      <script type="text/javascript">window.tbody_ready();</script>
@[for row in rows]@
      <tr>@[for cell in row]<td>@(cell)</td>@[end for]</tr>
@[end for]@
    </tbody>
  </table>
</body>
</html>
