# -*- encoding: utf-8 -*-
import xmlrpclib
import os
import sys
import time
import base64
import httplib2
from HTMLParser import HTMLParser
from urllib import urlencode
import argparse

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--host", "-H", metavar="host", default="127.0.0.1", help="Host [default: %(default)s]")
parser.add_argument("--port", "-p", metavar="port", default="8061", help="HTTP Port [default: %(default)s]")
parser.add_argument("--user", "-u", metavar="user", default="admin", help="User [default: %(default)s]")
parser.add_argument("--password", "-w", metavar="pwd", default="admin", help="Password [default: %(default)s]")
parser.add_argument('directory', action='store', help='directory')
o = parser.parse_args()

user= o.user
pwd = o.password
host = o.host
http_port = o.port



prefix_url = 'http://%s:%s/' % (host, http_port)
list_url = '%sopenerp/database/backup' % (prefix_url, )
backup_url = '%sopenerp/database/do_backup' % (prefix_url, )
headers = {
    'Referer': '%s/openerp/database/backup' % (prefix_url, ),
    'Content-Type': 'application/x-www-form-urlencoded'
}

class MyHTMLParser(HTMLParser):
    dbs = []
    def handle_starttag(self, tag, attrs):
        if tag == 'option':
            attrs_dic = dict(attrs)
            if attrs_dic.get('value'):
                self.dbs.append(attrs_dic['value'])


cnx = httplib2.Http()
resp, content = cnx.request(list_url, "GET")
parser = MyHTMLParser()
parser.feed(content)
all_dbs = parser.dbs
parser.close()

target_dir = o.directory
if os.path.exists(target_dir):
    if os.listdir(target_dir) != []:
        print "Dir %s not empty" % (target_dir, )
        sys.exit(0)
else:
    os.mkdir(target_dir)

for db in all_dbs:
    print db
    resp, content = cnx.request(backup_url, 'POST', body=urlencode({'dbname': db, 'password': pwd}), headers=headers)
    if resp.get('content-disposition'):
        dump_short_name = resp['content-disposition'].split('=')[1].replace('"','')
    else:
        dump_short_name = '%s-%s.dump' % (db, time.strftime('%Y%m%d-%H%M%S'))
    dump_path = os.path.join(target_dir, dump_short_name)
    f = open(dump_path, 'wb')
    f.write(content)
    f.close()
