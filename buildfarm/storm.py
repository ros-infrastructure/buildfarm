#!/usr/bin/env python

# Software License Agreement (BSD License)
#
# Copyright (c) 2011, Willow Garage, Inc.
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

import base64
import urllib2
import json
import time

pending_status_identifiers = ['Building', 'Building (Pending)',
                              'Created', 'Booting', 'Provisioning',
                              'Shutdown']  # Shutdown is a hack #FIXME #TODO


class StormAPI:
    def __init__(self, username, password, root_password):
        #self.password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        #self.password_mgr.add_password(None, 'https://api.stormondemand.com',
        #                               username, password)
        #self.handler = urllib2.HTTPBasicAuthHandler(self.password_mgr)
        #self.opener = urllib2.build_opener(self.handler)

        self.username = username
        self.password = password  # store for creation
        self.root_password = root_password

    def open(self, request):
        request.add_unredirected_header('Authorization', "Basic {0}".format(base64.b64encode('{0}:{1}'.format(self.username, self.password))))
        return urllib2.urlopen(request)

    def storm_server_available(self, domain):
        url = 'https://api.stormondemand.com/Storm/Server/available'
        values = {'params': {"domain": domain}}
        jsondump = json.dumps(values)
        request = urllib2.Request(url, jsondump)
        response = self.open(request)
        d = json.loads(response.read())
        if 'domain' in d:
            return d['domain']
        return None

    def account_paymethod_balance(self):
        url = 'https://api.stormondemand.com/Account/Paymethod/balance'
        request = urllib2.Request(url)
        response = self.open(request)
        d = json.loads(response.read())
        if 'balance' in d:
            return d['balance']
        return None

    def billing_payment_make(self, amount):
        url = 'https://api.stormondemand.com/v1/Billing/Payment/make'
        values = {'params':
                      {'amount': amount}
                  }
        jsondump = json.dumps(values)
        request = urllib2.Request(url, jsondump)
        response = self.open(request)
        d = json.loads(response.read())
        if 'amount' in d:
            return d['amount']
        return None

    def account_limits_servers(self):
        url = 'https://api.stormondemand.com/Account/Limits/servers'
        request = urllib2.Request(url)
        response = self.open(request)
        d = json.loads(response.read())
        if 'limit' in d:
            return int(d['limit'])
        return None

    def storm_server_create(self, backup_enabled, backup_plan, bandwidth_quota,
                            config_id, domain, image_id,
                            ip_count, password, template):
        raise NotImplemented

    def storm_server_create_preconfig(self, hostname, config_id=3,
                                      public_key=None):
        url = 'https://api.stormondemand.com/Storm/Server/create'
        values = {'params':
                  {"backup_enabled": 0,
                   "bandwidth_quota": 0,
                   "config_id": config_id,
                   "domain": hostname,
                   "password": self.root_password,
                   "public_ssh_key": public_key,
                   "template": 'UBUNTU_1204_UNMANAGED',
                   "zone": 12,
                   }
                  }
        jsondump = json.dumps(values)
        request = urllib2.Request(url, jsondump)
        response = self.open(request)
        d = json.loads(response.read())
        return d

    def storm_server_destroy(self, uniq_id):
        url = 'https://api.stormondemand.com/Storm/Server/destroy'
        values = {'params': {"uniq_id": uniq_id}}
        jsondump = json.dumps(values)
        request = urllib2.Request(url, jsondump)
        response = self.open(request)
        d = json.loads(response.read())
        if 'destroyed' in d:
            return d['destroyed']
        return None

    def storm_server_details(self, uniq_id):
        url = 'https://api.stormondemand.com/Storm/Server/details'
        values = {'params': {"uniq_id": uniq_id}}
        jsondump = json.dumps(values)
        request = urllib2.Request(url, jsondump)
        response = self.open(request)
        d = json.loads(response.read())
        return d

    def storm_server_status(self, uniq_id):
        url = 'https://api.stormondemand.com/Storm/Server/status'
        values = {'params': {"uniq_id": uniq_id}}
        jsondump = json.dumps(values)
        try:
            request = urllib2.Request(url, jsondump)
        except URLError, ex:
            print "Failed to get url %s with exception %s" % (url, ex)
            return None
        response = self.open(request)
        try:
            d = json.loads(response.read())
            if 'status' in d:
            #print "status", d['status']
                return d['status']
        except URLError, ex:
            print "URLError, ex"
        return None

    def storm_server_list(self):
        url = 'https://api.stormondemand.com/Storm/Server/list'
        values = {'params': {  # "category": "Provisioned",
                             "page_size": 1000}}
        jsondump = json.dumps(values)
        request = urllib2.Request(url, jsondump)
        response = self.open(request)
        d = json.loads(response.read())
        if 'items' in d:
            return d['items']
        print "Error: d is ", d
        return None

    def storm_config_list(self):
        url = 'https://api.stormondemand.com/Storm/config/list'
        values = {'params': {"page_size": 1000, 'category': 'all'}}
        jsondump = json.dumps(values)
        request = urllib2.Request(url, jsondump)
        response = self.open(request)
        d = json.loads(response.read())
        if 'items' in d:
            return d['items']
        print "d is ", d
        return None

    def storm_network_zone_list(self):
        url = 'https://api.stormondemand.com/v1/Network/Zone/list'
        values = {'params': {"page_size": 1000}}
        jsondump = json.dumps(values)
        request = urllib2.Request(url, jsondump)
        response = self.open(request)
        d = json.loads(response.read())
        if 'items' in d:
            return d['items']
        print "d is ", d
        return None

    def storm_template_list(self):
        url = 'https://api.stormondemand.com/v1/Storm/Template/list'
        values = {'params': {"page_size": 1000}}
        jsondump = json.dumps(values)
        request = urllib2.Request(url, jsondump)
        response = self.open(request)
        d = json.loads(response.read())
        if 'items' in d:
            return d['items']
        print "d is ", d
        return None

    # Helper functions
    def wait_for_running(self, server_ids, timeout=30):
        running_servers = []
        failed_servers = []
        unreached_servers = server_ids
        count = 0
        sleep_time = 1.0
        while unreached_servers:
            count = count + 1
            index = count % len(unreached_servers)
            s = unreached_servers[index]
            try:
                status = self.storm_server_status(s)
            except urllib2.URLError as e:
                print " Failed to poll status continuing anyway. [%s]" % e
            print 'polled server %s: %s' % (s, status)
            if status == 'Running':
                running_servers.append(s)
                unreached_servers.remove(s)
            elif status not in pending_status_identifiers:
                print "wait_for_running unknown status ", status
                unreached_servers.remove(s)
                failed_servers.append(s)
            time.sleep(sleep_time)
            if sleep_time * count > timeout:
                print "wait_for_running timed out after %.2f second" % timeout
                break
        return (running_servers, unreached_servers, failed_servers)
