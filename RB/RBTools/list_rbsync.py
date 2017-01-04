#! /usr/bin/python -W ignore::DeprecationWarning

import sys
import getpass
import subprocess
from tempfile import NamedTemporaryFile
from lib import jira_lib
import os
from configobj import ConfigObj

config_file = os.path.realpath(os.path.expanduser('~/RBconfig'))
cfg = ConfigObj(config_file)

jira_url = cfg['jira_url']
jira_user = cfg['jira_user']
passwd = cfg['jira_pass']
rb_server_url = cfg['rb_server_url']

fileobj = NamedTemporaryFile('wr')
subprocess.call(['./lib/list_rb.sh'], stdout=fileobj)
fileobj.seek(0)

if not passwd:
    passwd = getpass.getpass('Jira Password : ')
j = jira_lib.Jira(jira_url, jira_user, passwd)

for rb in fileobj:
    rb = rb.strip()
    issues = j.search("Runbot ~ 'http://%s.%s'" % (rb, rb_server_url), fixVersion=True)
    st = []
    for k in issues:
        st.append(issues[k])
    if not st or st == [None]:
        print "%s: no associated Jira issue"%(rb,)
    else:
        print "%s: %s"%(rb, ' '.join(st))

fileobj.close()
