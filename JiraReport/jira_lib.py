#! /usr/bin/python

import httplib2
import urllib
import json
import re
import SOAPpy
import SOAPpy.Types
from mx import DateTime

custom = {'web': 'customfield_10061', 'wm': 'customfield_10064', 'addons': 'customfield_10063', 'server': 'customfield_10062', 'groupedwm': 'customfield_10065', 'developer': 'customfield_10020', 'runbot_url': 'customfield_10050', 'data': 'customfield_10070', 'Release Priority': 'customfield_10040'}
class Jira():

    def __init__(self, jira_url, username, password):
        self.jira_url = jira_url
        self.headers = {'Content-Type' : 'application/json'}
        self.cache = {}

        if self.jira_url[-1] != '/':
            self.jira_url += '/'

        self.auth_url = "%srest/auth/latest/session"%(self.jira_url)
        auth = {'username': username, 'password': password}
        self.cnx = httplib2.Http()
        resp, content = self.cnx.request(self.auth_url, "POST", body=json.dumps(auth), headers=self.headers )
        ct = json.loads(content)
        self.headers['Cookie'] = "%s=%s"%(ct['session']['name'], ct['session']['value'])

    def __del__(self):
        self.cnx.request(self.auth_url, 'DELETE', headers=self.headers )

    def get_info(self, key):
        if key not in self.cache:
            resp, content = self.cnx.request("%srest/api/latest/issue/%s"%(self.jira_url, key),
                    "GET", headers=self.headers)
            self.cache[key] = json.loads(content)
        return self.cache[key]

    def get_value_dict(self, key, value, default=False, field1='value', field2='name' ):
        info = self.get_info(key)
        return info.get('fields', {}).get(value, {}).get(field1, {}).get(field2, default)

    def get_value(self, key, value, default=False, field='value'):
        info = self.get_info(key)
        return info.get('fields', {}).get(value, {}).get(field, default)

    def get_jira_url(self, key):
        return "%sbrowse/%s"%(self.jira_url, key)

class Jira_Soap():

    def __init__(self, jira_url, username, password):
        self.soap = SOAPpy.WSDL.Proxy(jira_url+'rpc/soap/jirasoapservice-v2?wsdl')
        self.auth = self.soap.login(username, password)

    def search(self, cond, limit=1000):
        return self.soap.getIssuesFromJqlSearch(self.auth, cond, limit)
