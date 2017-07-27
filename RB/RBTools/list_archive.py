#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getpass
from lib import jira_lib
import os
from configobj import ConfigObj

config_file = os.path.realpath(os.path.expanduser('~/RBconfig'))
cfg = ConfigObj(config_file)

jira_url = cfg['jira_url']
jira_user = cfg['jira_user']
passwd = cfg['jira_pass']
rb_server_url = cfg['rb_server_url']

path_dir = '/home'
home_dir = [f for f in os.listdir(path_dir) if os.path.isdir(os.path.join(path_dir, f)) and not os.path.exists(os.path.join(path_dir, f, 'archive'))]
if not passwd:
    passwd = getpass.getpass('Jira Password : ')
j = jira_lib.Jira(jira_url, jira_user, passwd)

for rb in home_dir:
    rb = rb.strip()
    issues = j.search("Runbot ~ 'http://%s.%s'" % (rb, rb_server_url), fixVersion=True)
    if not issues:
        issues = j.search("Runbot ~ 'https://%s.%s'" % (rb, rb_server_url), fixVersion=True)
    st = []
    for k in issues:
        st.append(issues[k])
    if not st or st == [None]:
        print "%s: no associated Jira issue"%(rb,)
    else:
        print "%s: %s"%(rb, ' '.join(st))

