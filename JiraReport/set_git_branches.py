#!/usr/bin/env python
import os, sys
import datetime
import git
from requests.packages import urllib3
# disable tls warning with jira
urllib3.disable_warnings()
import jira
from configobj import ConfigObj
import re

DRY_RUN = False
TOUCH = '/home/template/jira-git_lastsync'
local_repo = '/home/template/unifield-server.git'

if DRY_RUN:
    sys.stdout.write("DRY RUN MODE: JIRA WILL NOT BE UPDATED\n")

dev_map = {
    'jfb': 'jfb',
    'dk': 'd.kemps',
}
config_file = os.path.realpath(os.path.expanduser('~/RBconfig'))
cfg = ConfigObj(config_file)
jira_url = cfg.get('jira_url')
jira_user = cfg.get('jira_user')
jira_pass = cfg.get('jira_pass')

interval = 5
if not jira_url or not jira_user or not jira_pass:
    sys.stderr.write("Missing Jira info, please check ~/RBconfig\n")
    sys.exit(1)

j_obj = jira.JIRA(jira_url, options={'check_update': False}, basic_auth=(jira_user, jira_pass))

repo = git.Repo(local_repo)
repo.remotes.origin.fetch()
remote_url = '%s/tree/' % repo.remotes.origin.url.strip('.git')

last_mod = datetime.datetime.now() - datetime.timedelta(days=interval)
to_set = {}

for r_branch in repo.remote().refs:
    branch_split = r_branch.name.lower().split('/')
    if branch_split[0] == 'origin' and branch_split[1] in dev_map:
        m = re.search('(US-[0-9]+)$', branch_split[2], flags=re.IGNORECASE)
        commit_date = datetime.datetime.fromtimestamp(r_branch.commit.committed_date)
        if m and commit_date >= last_mod:
            ticket = m.group(1).lower()
            url = '%s%s' % (remote_url, '/'.join(r_branch.name.split('/')[1:]))
            to_set.setdefault(ticket, []).append((dev_map[branch_split[1]], url))

for k, info in to_set.items():
    for dev, git_url in info:
        try:
            ticket = j_obj.issue(k, fields='customfield_10065,customfield_10020,status,assignee')
        except:
            sys.stderr.write("Issue not found %s\n" % k)
            continue

        if ticket.fields.status.name not in ('Open', 'In Progress'):
            continue

        to_write = {}
        if not ticket.fields.assignee or ticket.fields.assignee.name not in dev:
            sys.stdout.write("Nothing done on %s: Jira assignee (%s) and lp dev (%s) mismatch\n" % (k, ticket.fields.assignee and ticket.fields.assignee.name or 'None', dev.keys()))
            continue

        jira_dev = ticket.fields.assignee.name
        git_jira_branch = ticket.fields.customfield_10065
        if not git_jira_branch:
            to_write['customfield_10065'] = git_url
            if not ticket.fields.customfield_10020 and 'customfield_10020' not in to_write:
                to_write['customfield_10020'] = {'name': dev}

        if to_write:
            if ticket.fields.status.name == 'Open':
                # 231 : In Progress
                sys.stdout.write("Update trans %s, %s\n" % (k, to_write))
                if not DRY_RUN:
                    j_obj.transition_issue(ticket, '231', fields=to_write)
            else:
                sys.stdout.write("Update values %s %s\n" % (k, to_write))
                if not DRY_RUN:
                    ticket.update(fields=to_write)

if TOUCH:
    open(TOUCH, 'wb').close()

