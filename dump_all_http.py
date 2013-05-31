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
parser.add_argument("--port", "-p", metavar="port", default=None, help="HTTP/XMLRPC Port [default: 8061/8069 (depending on protocol used)]")
parser.add_argument("--user", "-u", metavar="user", default="admin", help="User [default: %(default)s]")
parser.add_argument("--password", "-w", metavar="pwd", default="admin", help="Password [default: %(default)s]")
parser.add_argument("--exclude", "-x", metavar="exclude", default=False, help="Comma separated list of dbs to exclude")
parser.add_argument("--include", "-i", metavar="include", default=False, help="Comma separated list of dbs to include")
parser.add_argument("--overwrite", "-o", default=False, action="store_true", help="Do not complain if target dir exists")
group = parser.add_mutually_exclusive_group()
group.add_argument("--http", action="store_true", default=True, help="Use http [default: %(default)s]")
group.add_argument("--xmlrpc", action="store_true", default=False, help="Use xmlrpc [default: %(default)s]")
parser.add_argument('directory', action='store', help='directory')
o = parser.parse_args()

user= o.user
pwd = o.password
host = o.host
if o.port is None:
    if o.xmlrpc:
        o.port = 8069
    else:
        o.port = 8061
port = o.port

exclude = []
include = []
if o.exclude:
    exclude = o.exclude.split(',')
if o.include:
    include = o.include.split(',')


prefix_url = 'http://%s:%s/' % (host, port)
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

def _filter(dbs, exclude, include):
    to_dump = []
    for db in dbs:
        if (not include and db not in exclude) or db in include:
            to_dump.append(db)
    return to_dump

def list_dbs(o):
    if o.xmlrpc:
        sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/db'%(host, port))
        return sock.list()
    cnx = httplib2.Http()
    resp, content = cnx.request(list_url, "GET")
    parser = MyHTMLParser()
    parser.feed(content)
    parser.close()
    return parser.dbs

target_dir = o.directory
if os.path.exists(target_dir):
    if not o.overwrite and os.listdir(target_dir) != []:
        print "Dir %s not empty" % (target_dir, )
        sys.exit(0)
else:
    os.mkdir(target_dir)

all_dbs = _filter(list_dbs(o), exclude, include)

ret = ''
while ret.lower() not in ('y', 'n'):
    print "Server %s:%s, proto %s, do you really want to dump %s ? [y/n]" % (host, port, o.xmlrpc and "XMLRPC" or "HTTP", " ".join(all_dbs))
    ret = raw_input()
if ret.lower() == 'n':
    print "Abort"
    sys.exit(0)

for db in all_dbs:
    print db
    if o.xmlrpc:
        sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/db'%(host, port))
        content = base64.decodestring(sock.dump(pwd, db))
        dump_path = os.path.join(target_dir, '%s-%s.dump' % (db, time.strftime('%Y%m%d-%H%M%S')))
    else:
        cnx = httplib2.Http()
        resp, content = cnx.request(backup_url, 'POST', body=urlencode({'dbname': db, 'password': pwd}), headers=headers)
        if resp.get('content-disposition'):
            dump_short_name = resp['content-disposition'].split('=')[1].replace('"','')
        else:
            dump_short_name = '%s-%s.dump' % (db, time.strftime('%Y%m%d-%H%M%S'))
        dump_path = os.path.join(target_dir, dump_short_name)
    f = open(dump_path, 'wb')
    f.write(content)
    f.close()
    if not os.path.getsize(dump_path):
        print "Warning %s is empty !" % (dump_path, )

