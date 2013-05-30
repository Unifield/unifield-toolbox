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
o = parser.parse_args()

user= o.user
pwd = o.password
host = o.host
port = o.port

ret = ''
sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/db'%(host, port))
dbs = sock.list()
while ret.lower() not in ('y','n'):
    print "Server %s, do you really want to delete %s ? [y/n]" % (host, " ".join(dbs))
    ret = raw_input()
if ret.lower() == 'n':
    print "Nothing done"
    sys.exit(0)

for db in dbs:
    print 'Deleting %s ...' % (db, )
    try:
        dump = sock.drop(pwd, db)
    except Exception, e:
        print "Can't delete %s %s" % (db, e)
