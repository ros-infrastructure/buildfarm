@{
import time
static_asset_version=1003
}
<!DOCTYPE html>
<html>
<head>
  <title>ROS @(' '.join([d.capitalize() for d in distro_names])) - version compare page - @(time.strftime('%Y-%m-%d %H:%M:%S %Z', start_time))</title>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8"/>

  <script type="text/javascript" src="@(resource_path)/js/zepto.min.js"></script>
  <script type="text/javascript">
    window.repos = @(repr(repos));
  </script>
  <script type="text/javascript" src="@(resource_path)/js/setup.js?@(static_asset_version)"></script>

  <link rel="stylesheet" href="@(resource_path)/css/status_page.css?@(static_asset_version)" />
  <link rel="stylesheet" href="@(resource_path)/css/compare_page.css?@(static_asset_version)" />
</head>
<body>
  <script type="text/javascript">window.body_ready();</script>
  <div class="top wetdry">
    <h1><img src="http://wiki.ros.org/custom/images/ros_org.png" alt="ROS.org" width="150" height="32" /></h1>
    <h2>ROS @(' '.join([d.capitalize() for d in distro_names])) Version Compare</h2>
  </div>
  <div class="top search">
    <form>
      <input type="text" name="q" id="q" />
      <p>Quick:
        <a href="?q=" title="Show all repos">all</a>,
        <a href="?q=diff_patch" title="Filter packages which are only differ in the patch version">different patch version</a>,
        <a href="?q=downgrade_version" title="Filter packages which disappear by a sync from shadow-fixed to public">downgrade</a>,
        <a href="?q=diff_branch_same_version" title="Filter packages which are are released from different branches but have same minor version">same version from different branches</a>,
      </p>
      <p id="search-count"></p>
    </form>
  </div>
  <table>
    <thead>
       <tr>
@[for header in headers]@
      <th><div>@(header)</div></th>
@[end for]@
      </tr>
    </thead>
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
