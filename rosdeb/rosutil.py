# Software License Agreement (BSD License)
#
# Copyright (c) 2010, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Revision $Id: rosutil.py 16945 2012-08-31 16:45:33Z tfoote $
# $Author: tfoote $

import os
import subprocess
import tempfile


def checkout_svn_to_tmp(name, uri):
    """
    Checkout an SVN tree to the tmp dir.

    Utility routine -- need to replace with vcs

    @return: temporary directory that contains checkout of SVN tree in
    directory 'name'. temporary directory will be a subdirectory of
    OS-provided temporary space.
    @rtype: str
    """
    tmp_dir = tempfile.mkdtemp()
    dest = os.path.join(tmp_dir, name)
    print 'Checking out a fresh copy of %s from %s to %s...'%(name, uri, dest)
    subprocess.check_call(['svn', 'co', uri, dest])
    return tmp_dir

def send_email(smtp_server, from_addr, to_addrs, subject, text):
    import smtplib
    from email.mime.text import MIMEText

    msg = MIMEText(text)

    msg['From'] = from_addr
    msg['To'] = to_addrs
    msg['Subject'] = subject

    s = smtplib.SMTP(smtp_server)
    print 'Sending mail to %s'%(to_addrs)
    try:
        s.sendmail(msg['From'], [msg['To']], msg.as_string())
    except Exception, ex:
        print "Sending email failed with exception: %s" % ex
    s.quit()

