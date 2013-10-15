@{import time}
<!DOCTYPE html>
<html>
<head>
  <title>ROS @(rosdistro.capitalize()) - build status page - @(time.strftime('%Y-%m-%d %H:%M:%S %Z', start_time))</title>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8"/>

  <script type="text/javascript" src="js/zepto.min.js"></script>
  <script type="text/javascript">
    window.repos = @(repr(repos));
    window.job_url_templates = @(repr([c['job_url'] for c in metadata_columns[3:]]));
  </script>
  <script type="text/javascript" src="js/setup.js"></script>

  <link rel="stylesheet" href="css/status_page.css" />
</head>
<body>
  <script type="text/javascript">window.body_ready();</script>
  <div class="top wetdry">
    <h1><img src="http://wiki.ros.org/custom/images/ros_org.png" alt="ROS.org" /></h1>
    <h2>Debian Build Status</h2>
    <ul>
      <li><strong>wet</strong> - <a href="http://ros.org/wiki/catkin">catkin</a></li> 
      <li><strong>dry</strong> - <a href="http://ros.org/wiki/rosbuild">rosbuild</a></li> 
    </ul>
  </div>
  <div class="top repos">
    <p class="squares"><a class="w">1</a> <a class="w">2</a> <a class="w">3</a></p>
    <ol>
      <li>building repo</li>
      <li>shadow-fixed repo</li>
      <li>ros/public repo</li>
    </ol>
  </div>
  <div class="top colors">
    <ul class="squares">
      <li><a></a> same version</li>
      <li><a class="o"></a> different version</li>
      <li><a class="m"></a> missing</li>
      <li><a class="obs"></a> obsolete</li>
      <li><a class="i"></a> intentionally missing</li> 
    </ul> 
  </div>
  <div class="top search">
    <form>
      <input type="text" name="q" id="q" />
      <p>Search for any text, or the following keywords:<br/>
         <a href="?q=diff">diff</a>,
         <a href="?q=sync">sync</a>,
         <a href="?q=regression">regression</a>,
         <a href="?q=blue">blue</a>,
         <a href="?q=red">red</a>,
         <a href="?q=yellow">yellow</a>,
         <a href="?q=gray">gray</a></p>
    </form> 
  </div>
  <table>
    <thead>
       <tr>
@[for header, row_count in zip(headers, row_counts)]@
      <th><div>@(header)</div>@[for count in row_count]<span class="sum">@(count)</span>@[end for]</th>
@[end for]@
      </tr>    
    </thead>
    <!-- <tfoot>
      <tr>
@[for header in headers]@
      <th>@(header)</th>
@[end for]@
      </tr>
    </tfoot> -->
    <tbody>
      <script type="text/javascript">window.tbody_ready();</script>
@[for row in rows]@
      <tr>@[for cell in row]<td>@(cell)</td>@[end for]</tr>
@[end for]@
    </tbody>
  </table>
</body>
<script type="text/javascript">window.body_done();</script>
</html>
