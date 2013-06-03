#!/usr/bin/python

from bzrlib.branch import Branch
from bzrlib.plugins.launchpad.lp_directory import LaunchpadDirectory

import sys
import os
import re
from JiraReport import jira_lib

import argparse
import getpass


parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument('--jira-user', metavar='JIRA_USER', default='jfb', help='Jira User (default: %(default)s)')
parser.add_argument('--jira-url', metavar='JIRA_URL', default='http://jira.unifield.org/', help='Jira url (default: %(default)s)')
parser.add_argument('--jira-passwd', '-p',  metavar='JIRA_PASSWORD', default=False, help='Jira password')
parser.add_argument('--out-file', '-o',  metavar='Out file', default='issues', help='File name')
parser.add_argument('--use-rep', metavar='directory', default=False, help='Do not connect to launchpad but use an existing working tree')
parser.add_argument('from_tag', action='store', help='From tag')
parser.add_argument('to_tag', action='store', help='To tag')
parser.add_argument('jira_tag', action='store', help="List of Jira versions")

o = parser.parse_args()
if not o.jira_passwd:
    o.jira_passwd = getpass.getpass('Jira Password : ')

jira_list = '%s-jira.txt' % (o.out_file)
commit_list = '%s-commit.txt' % (o.out_file)

if os.path.exists(jira_list):
    print "File %s: exists" % (jira_list)
    sys.exit(1)
if os.path.exists(commit_list):
    print "File %s: exists" % (commit_list)
    sys.exit(1)

rex = re.compile('(\s|^)((UF|UTP|SP|AIO|OEB|ITWG)-[0-9]+)', re.I)

all_issues = {}

for branch in ('lp:unifield-wm', 'lp:~unifield-team/unifield-wm/sync_module_prod', 'lp:unifield-addons', 'lp:unifield-server', 'lp:unifield-web'):
    if not o.use_rep:
        directory = LaunchpadDirectory()
        d = directory._resolve(branch)
    else:
        d = os.path.join(o.use_rep, os.path.basename(branch.split(':')[1]))
    wk = Branch.open(d)
    from_rev_id = wk.revision_id_to_dotted_revno(wk.tags.lookup_tag(o.from_tag))[0]
    to_rev_id = wk.revision_id_to_dotted_revno(wk.tags.lookup_tag(o.to_tag))[0]

    for rev in wk.revision_history()[from_rev_id:to_rev_id]:
        msg = wk.repository.get_revision(rev).message
        found = False
        for m in re.finditer(rex, msg):
            found = True
            all_issues[m.group(0).upper().strip()] = 1

        if not found:
            print "Log %s Nothing found in %s" % (branch, msg)

issues = all_issues.keys()
issues.sort()

soap = jira_lib.Jira_Soap(o.jira_url, o.jira_user, o.jira_passwd)
jira_issues = {}
for ji in soap.search('fixVersion in (%s) and status not in (Open, Reopened, "In Progress")' % (','.join(map(lambda x:'"%s"'%x, o.jira_tag.split(","))))):
    jira_issues[ji['key']] = 1
j_issues = jira_issues.keys()
j_issues.sort()

fj = open(jira_list, 'w')
fc = open(commit_list, 'w')

for lpiss in issues:
    if lpiss not in j_issues:
        print "Found in branch but not in Jira: %s" % (lpiss, )
    fc.write("%s\n" % lpiss)

for jiss in j_issues:
    if jiss not in issues:
        print "Found in Jira but not in branch: %s" % (jiss, )
    fj.write("%s\n" % jiss)
fc.close()
fj.close()

