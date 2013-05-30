# -*- encoding: utf-8 -*-
import xmlrpclib
import os
import sys
import time
import base64
import argparse

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--host", "-H", metavar="host", default="127.0.0.1", help="Host [default: %(default)s]")
parser.add_argument("--port", "-p", metavar="port", default="8069", help="XMLRPC Port [default: %(default)s]")
parser.add_argument("--user", "-u", metavar="user", default="admin", help="User [default: %(default)s]")
parser.add_argument("--password", "-w", metavar="pwd", default="admin", help="Password [default: %(default)s]")
parser.add_argument('directory', action='store', help='directory')
o = parser.parse_args()

user= o.user
pwd = o.password
host = o.host
port = o.port

target_dir = o.directory

if os.path.exists(target_dir):
    if os.listdir(target_dir) != []:
        print "Directory %s not empty" % (target_dir, )
        sys.exit(0)
else:
    os.mkdir(target_dir)

sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/db'%(host, port))
for db in sock.list():
    print db
    dump = sock.dump(pwd, db)
    db_dump = os.path.join(target_dir, '%s-%s.dump' % (db, time.strftime('%Y%m%d-%H%M%S')))
    f = open(db_dump, 'wb')
    f.write(base64.decodestring(dump))
    f.close()
