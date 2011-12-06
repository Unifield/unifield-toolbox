#! /usr/bin/python

import httplib2
import urllib
import json
import re
import SOAPpy
import SOAPpy.Types

custom = {'web': 'customfield_10061', 'wm': 'customfield_10064', 'addons': 'customfield_10063', 'server': 'customfield_10062', 'groupedwm': 'customfield_10065', 'developer': 'customfield_10020', 'runbot_url': 'customfield_10050'}
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

    def get_info(self, key):
        resp, content = self.cnx.request("%srest/api/latest/issue/%s"%(self.jira_url, key),
                "GET", headers=self.headers)
        return json.loads(content)

    def get_state(self, key):
        issue = self.get_info(key)
        runbot = issue.get('fields', {}).get(custom['runbot_url'], {}).get('value', "")
        m = re.match('\s*(http://)?(\w+)',runbot)
        declared_runbot = False
        if m:
            declared_runbot = m.group(2)
        return (issue.get('fields', {}).get('status', {}).get('value', {}).get('name'), declared_runbot)

    def get_user_mail(self, user):
        if not user:
            return False
        resp, content = self.cnx.request("%srest/api/latest/user?username=%s"%(self.jira_url, user),
                "GET", headers=self.headers)
        ret = json.loads(content)
        return ret.get('emailAddress', False)

    def get_branches(self, key):
        issue = self.get_info(key)
        ret = {}
        for t in ['web', 'wm', 'addons', 'server', 'groupedwm']:
            ret[t] = issue.get('fields', {}).get(custom[t], {}).get('value', False)
        ret['comment'] = issue.get('fields', {}).get('summary', {}).get('value', False)
        user = issue.get('fields', {}).get(custom['developer'], {}).get('value', {}).get('name', False)
        if not user:
            user = issue.get('fields', {}).get('assignee', {}).get('value', {}).get('name', False)
        ret['email'] = self.get_user_mail(user)
        return ret

class Jira_Soap():

    def __init__(self, jira_url, username, password):
        self.soap = SOAPpy.WSDL.Proxy(jira_url+'rpc/soap/jirasoapservice-v2?wsdl')
        self.auth = self.soap.login(username, password)

    def write_runbot(self, key, runbot_url):
        self.soap.updateIssue(self.auth, key, [{'id': custom['runbot_url'], 'values': runbot_url}])

    def click_deploy(self, key, runbot_url):
        self.soap.progressWorkflowAction(self.auth, key, '711', [])
