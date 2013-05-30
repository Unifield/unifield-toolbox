# -*- encoding: utf-8 -*-
import xmlrpclib
import os
import sys
import time
import base64

user='admin'
pwd = 'admin'

# xmlrpc port
port = 8069
#host = '10.0.0.174'
host = '127.0.0.1'

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
    print 'Delete %s' % (db, )
    try:
        dump = sock.drop(pwd, db)
    except Exception, e:
        print "Can't delete %s %s" % (db, e)
