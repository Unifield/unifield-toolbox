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

    def get_state(self, key):
        issue = self.get_info(key)
        runbot = issue.get('fields', {}).get(custom['runbot_url'], {}).get('value', "")
        m = re.match('\s*(http://)?(\w+)',runbot)
        declared_runbot = False
        if m:
            declared_runbot = m.group(2)
        other_info = {}
        other_info['Assignee'] = issue.get('fields', {}).get('assignee',{}).get('value',{}).get('displayName')
        other_info['Developer'] = issue.get('fields', {}).get(custom['developer'],{}).get('value',{}).get('displayName')
        other_info['Reporter'] = issue.get('fields', {}).get('reporter',{}).get('value',{}).get('displayName')
        other_info['Summary'] = issue.get('fields', {}).get('summary', {}).get('value')
        other_info['Updated'] = ''
        other_info['Fix Version'] = ''
        if issue.get('fields', {}).get('fixVersions', {}).get('value'):
            other_info['Fix Version'] = issue.get('fields', {}).get('fixVersions', {}).get('value',[{}])[-1].get('name','')
        other_info['Release Prio'] = issue.get('fields', {}).get(custom.get('Release Priority'), {}).get('value','')
        other_info['uf'] = key.replace('UF-','')
        lastupdate = issue.get('fields', {}).get('updated', {}).get('value','')
        if lastupdate:
            last_updated = DateTime.DateFrom(lastupdate)
            other_info['updated_ticks'] = last_updated.ticks()
            other_info['Updated'] = last_updated.strftime('%d/%m/%Y %H:%M')
        other_info['Parent'] = False

        parent = issue.get('fields', {}).get('parent', {}).get('value',{}).get('issueKey')
        if parent:
            other_info['Parent'] = "%s %s"%(parent, self.get_info(parent).get('fields', {}).get('summary', {}).get('value'))
        for k in ['web', 'wm', 'addons', 'server', 'groupedwm', 'data', 'runbot_url']:
            v = issue.get('fields', {}).get(custom[k], {}).get('value', '')
            if v:
                other_info[k] = v
        last_comment = issue.get('fields', {}).get('comment',{}).get('value', [])
        if last_comment:
            date_last_upd = DateTime.DateFrom(last_comment[-1].get('updated'))
            other_info['last_comment_header'] = '%s %s'%(last_comment[-1].get('author',{}).get('displayName', ''),date_last_upd.strftime('%d/%m/%Y %H:%M'))
            content = last_comment[-1].get('body', '')
            if len(content) > 300:
                content = content[0:300]+'...'
            other_info['last_comment'] = content
        other_info['key'] = key
        return (issue.get('fields', {}).get('status', {}).get('value', {}).get('name'), declared_runbot, other_info)

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
        for t in ['web', 'wm', 'addons', 'server', 'groupedwm', 'data']:
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
    
    def search_runbot(self, name):
        cond = 'Runbot ~ "%s~"'%(name, )
        ret = []
        for issue in self.soap.getIssuesFromJqlSearch(self.auth, cond, 10):
            ret.append(issue['key'])
        return ret

