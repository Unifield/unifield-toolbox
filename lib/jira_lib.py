#! /usr/bin/python

import httplib2
import urllib
import json
import re
class Jira():
    jira_url = False
    headers = {'Content-Type' : 'application/json'}    
    def __init__(self, jira_url, username, password):
        self.jira_url = jira_url

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

    def get_state(self, key):
        resp, content = self.cnx.request("%srest/api/latest/issue/%s"%(self.jira_url, key),
                "GET", headers=self.headers)
        issue = json.loads(content)
        runbot = issue.get('fields', {}).get('customfield_10050', {}).get('value', "")
        m = re.match('(http://)?(\w+)',runbot)
        declared_runbot = False
        if m:
            declared_runbot = m.group(2)
        return (issue.get('fields', {}).get('status', {}).get('value', {}).get('name'), declared_runbot)
