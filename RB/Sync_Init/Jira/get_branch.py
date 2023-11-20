#! /usr/bin/python
# -*- encoding: utf-8 -*-

import sys
import os
from configobj import ConfigObj

from requests.packages import urllib3
# disable tls warning with jira
urllib3.disable_warnings()
import jira

if len(sys.argv) < 1:
    sys.stderr.write("Missing issue key")
    sys.exit(1)

config_file = os.path.realpath(os.path.expanduser('~/RBconfig'))
cfg = ConfigObj(config_file)
jira_url = cfg.get('jira_url')
jira_user = cfg.get('jira_user')
jira_pass = cfg.get('jira_pass')

if not jira_url or not jira_user or not jira_pass:
    sys.stderr.write("Missing Jira info, please check ~/RBconfig\n")
    sys.exit(1)

try:
    j_obj = jira.JIRA(jira_url, options={'check_update': False}, basic_auth=(jira_user, jira_pass))
    issue = j_obj.issue(sys.argv[1])
except jira.exceptions.JIRAError, error:
    if error.status_code == 401:
        message = 'Unauthorized'
    else:
        message = error.text
    sys.stderr.write("Jira Error %s: %s\n" % (error.status_code, message))
    sys.exit(1)


server_branch = issue.fields.customfield_10065 or issue.fields.customfield_10062
web_branch = issue.fields.customfield_10061
dev = issue.fields.customfield_10020
if not dev:
    sys.stderr.write("Jira Error: no dev on issue %s\n" % (sys.argv[1]))
    sys.exit(1)

user_mail = dev.emailAddress.split('@')[0]
if '.' in user_mail:
    user_mail = ''.join([x[0] for x in user_mail.split('.')])

print server_branch and server_branch.replace('https://code.launchpad.net/', 'lp:') or 'lp:unifield-server'
print web_branch and web_branch.replace('https://code.launchpad.net/', 'lp:') or '-'
print user_mail


