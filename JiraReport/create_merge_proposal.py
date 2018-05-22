#!/usr/bin/env python
import os, sys
from launchpadlib.launchpad import Launchpad
from requests.packages import urllib3
# disable tls warning with jira
urllib3.disable_warnings()
import jira
import json
from configobj import ConfigObj


config_file = os.path.realpath(os.path.expanduser('~/RBconfig'))
cfg = ConfigObj(config_file)
jira_url = cfg.get('jira_url')
jira_user = cfg.get('jira_user')
jira_pass = cfg.get('jira_pass')

if not jira_url or not jira_user or not jira_pass:
    sys.stderr.write("Missing Jira info, please check ~/RBconfig\n")
    sys.exit(1)

j_obj = jira.JIRA(jira_url, options={'check_update': False}, basic_auth=(jira_user, jira_pass))
server_branches = []
web_branches = []

cachedir = os.path.expanduser("~/.launchpadlib/cache/")
launchpad = Launchpad.login_with('Jira-lp', 'production', cachedir)

browser = launchpad._browser
for issue in j_obj.search_issues("status in ('Runbot Validated', 'Runbot Available', 'Pre-Integrated')"):

    target_server_branch = launchpad.branches.getByUrl(url='lp:unifield-server/trunk')
    target_web_branch = launchpad.branches.getByUrl(url='lp:unifield-web/trunk')
    for x in issue.fields.fixVersions:
        if x.name.startswith('UF5'):
            target_server_branch = launchpad.branches.getByUrl(url='lp:unifield-server/uf5')
            target_web_branch = launchpad.branches.getByUrl(url='lp:unifield-web/uf5')
        elif x.name.startswith('UF6'):
            target_server_branch = launchpad.branches.getByUrl(url='lp:unifield-server/uf6')
            target_web_branch = launchpad.branches.getByUrl(url='lp:unifield-web/uf6')
        elif x.name.startswith('UF7'):
            target_server_branch = launchpad.branches.getByUrl(url='lp:unifield-server/uf7')
            target_web_branch = launchpad.branches.getByUrl(url='lp:unifield-web/uf7')

    if issue.fields.customfield_10065:
        server_branches.append((target_server_branch, issue.fields.customfield_10065.replace('https://code.launchpad.net/', 'lp:')))
    if issue.fields.customfield_10062:
        server_branches.append((target_server_branch,issue.fields.customfield_10062.replace('https://code.launchpad.net/', 'lp:')))
    if issue.fields.customfield_10061:
        web_branches.append((target_web_branch, issue.fields.customfield_10061.replace('https://code.launchpad.net/', 'lp:')))


for target_branch, br in server_branches + web_branches:
    src_branch = launchpad.branches.getByUrl(url=br)
    link = src_branch.landing_targets_collection_link
    to_merge = True
    if link:
        b = json.loads(browser.get(link))
        if b['entries'] or src_branch == target_branch:
            to_merge = False
    if to_merge:
        try:
            src_branch.createMergeProposal(target_branch=target_branch)
            print 'To merge', br, target_branch
        except Exception, e:
            print "Unable to merge %s %s: %s", (br, target_branch, e)


