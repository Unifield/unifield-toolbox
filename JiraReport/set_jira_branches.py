#!/usr/bin/env python
import os, sys
from launchpadlib.launchpad import Launchpad
import datetime
from requests.packages import urllib3
# disable tls warning with jira
urllib3.disable_warnings()
import jira
from configobj import ConfigObj
import re

DRY_RUN = True

if DRY_RUN:
    sys.stdout.write("DRY RUN MODE: JIRA WILL NOT BE UPDATED\n")

dev_map = {
    'adn741': 'd.joguet',
    'fabien-morin': 'fabien',
    'jr.allen': 'jrallen',
    'jfb-tempo-consulting': 'jfb',
    'julie-w': 'julie.nuguet',
    'mallorymarcot': 'm.marcot',
    'qt-tempo-consulting': 'qt',
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

cachedir = os.path.expanduser("~/.launchpadlib/cache/")
launchpad = Launchpad.login_anonymously('find_branches','production',cachedir)


last_mod = (datetime.datetime.now() - datetime.timedelta(days=interval)).isoformat()
project_server = launchpad.projects['unifield-server']
project_web = launchpad.projects['unifield-web']
to_set = {}
for component, project in [('web', project_web), ('server', project_server)]:
    for b in project.getBranches(modified_since=last_mod):
        if b.lifecycle_status not in ["Abandoned", "Merged"] and b.registrant.name in dev_map:
            m = re.search('(US-[0-9]+)$', b.bzr_identity, flags=re.IGNORECASE)
            if m:
                ticket = m.group(1).lower()
                to_set.setdefault(ticket, {}).setdefault(dev_map[b.registrant.name], {}).update({component: b.web_link})

for k, dev in to_set.iteritems():
    try:
        ticket = j_obj.issue(k, fields='customfield_10065,customfield_10062,customfield_10020,customfield_10061,status,assignee')
    except:
        sys.stderr.write("Issue not found %s\n" % k)
        continue
    
    if ticket.fields.status.name not in ('Open', 'In Progress'):
        continue

    to_write = {}
    if ticket.fields.assignee.name not in dev:
        sys.stdout.write("Nothing done on %s: Jira assignee (%s) and lp dev (%s) mismatch\n" % (k, ticket.fields.assignee.name, dev.keys()))
        continue

    values = dev[ticket.fields.assignee.name]
    if 'server' in values:
        server_branch = ticket.fields.customfield_10065 or ticket.fields.customfield_10062
        if not server_branch:
            to_write['customfield_10062'] = values['server']
            if not ticket.fields.customfield_10020 and 'customfield_10020' not in to_write:
                to_write['customfield_10020'] = {'name': values['dev']}

    if 'web' in values and not ticket.fields.customfield_10061:
        to_write['customfield_10061'] = values['web']
        if not ticket.fields.customfield_10020 and 'customfield_10020' not in to_write:
            to_write['customfield_10020'] = {'name': values['dev']}

    if to_write:
        if ticket.fields.status.name == 'Open':
            # 231 : In Progress
            sys.stdout.write("Update trans %s\n" % k)
            if not DRY_RUN:
                j_obj.transition_issue(ticket, '231', fields=to_write)
        else:
            sys.stdout.write("Update values %s\n" % k)
            if not DRY_RUN:
                ticket.update(fields=to_write)

