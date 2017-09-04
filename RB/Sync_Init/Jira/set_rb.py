#! /usr/bin/python
# -*- encoding: utf-8 -*-

import sys
import os
from configobj import ConfigObj

from requests.packages import urllib3
# disable tls warning with jira
urllib3.disable_warnings()
import jira

if len(sys.argv) < 2:
    sys.stderr.write("Missing issue key or RB url")
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

rb = issue.fields.customfield_10050
if not rb or sys.argv[2] not in rb:
    if rb:
        new_rb = "%s\n%s" % (rb, sys.argv[2])
    else:
        new_rb = sys.argv[2]
    issue.update(fields={'customfield_10050': new_rb})
