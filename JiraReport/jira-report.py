#!/usr/bin/python -W ignore::DeprecationWarning

import sys
import os,re,subprocess,time
import argparse
import fileinput
from mako.template import Template
import ConfigParser
import jira_lib
import getpass
from datetime import datetime
import zipfile
import shutil
from mx import DateTime
import time
#return mako.template.Template(template).render(r=self)

#    if not o.jira_passwd:
#        o.jira_passwd = getpass.getpass('Jira Password : ')

#    jira = jira_lib.Jira(o.jira_url, o.jira_user, o.jira_passwd)
#    ret = jira.get_branches('UF-%s'%o.number.split(',')[0])
#sjira = jira_lib.Jira_Soap(o.jira_url, o.jira_user, o.jira_passwd)
#    jira = jira_lib.Jira(o.jira_url, o.jira_user, o.jira_passwd)

def format_date(date):
    if not date:
        return ""
    try:
        d= DateTime.ISO.ParseDateTime(date)
        return 'office:date-value="%s"'%d.strftime("%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return ""

def all_assignee(keys, rest):
    ret = {}
    for k in keys:
        ret[rest.get_value_dict(k, 'customfield_10020', field2='displayName', default="")] = True
    k = ret.keys()
    k.append('MCH')
    return k

def gen_ods(o):
    cond = 'project = UF AND issuetype in (Dev, WM-Bug, WM-Improvement, WM-ChangeRequest, "Technical Bug") AND component in (Finance, Supply) AND status in (Open, "In Progress", Reopened)'
    rest = jira_lib.Jira(o.jira_url, o.jira_user, o.jira_passwd)
    sjira = jira_lib.Jira_Soap(o.jira_url, o.jira_user, o.jira_passwd)
    keys = [x['key'] for x in sjira.search(cond)]
#    keys = ['UF-834']
#    issue = rest.get_info('UF-848').get('fields')
#    for l in issue:
#        print l
#        print issue[l]

    shutil.copyfile('template/devmeeting-tmpl.ods', o.out_file)
    zip = zipfile.ZipFile(o.out_file, 'a')
    mytemplate = Template(filename='template/content.xml', output_encoding='utf-8', input_encoding='utf-8')
    zip.writestr('content.xml', mytemplate.render(time=time, keys=keys, jira=rest, size=len(keys)+1, all_assignee=all_assignee(keys, rest), format_date=format_date))
    zip.close()

def main():
    os.chdir(os.path.normpath(os.path.dirname(__file__)))
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--jira-user', metavar='JIRA_USER', default='jfb', help='Jira User (default: %(default)s)')
    parser.add_argument('--jira-url', metavar='JIRA_URL', default='http://jira.unifield.org/', help='Jira url (default: %(default)s)')
    parser.add_argument('--jira-passwd', '-p',  metavar='JIRA_PASSWORD', default=False, help='Jira password')
    parser.add_argument('--out-file', '-o',  metavar='Out file', default='out.ods', help='File name')
    o = parser.parse_args()
    if not o.jira_passwd:
        o.jira_passwd = getpass.getpass('Jira Password : ')
    gen_ods(o)

if __name__ == '__main__':
    main()
