# -*- encoding: utf-8 -*-
import xmlrpclib
import csv

user='admin'
pwd = 'admin'

# xmlrpc port
port = 8069
#host = '10.0.0.174'
host = '127.0.0.1'

sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/db'%(host, port))
for db in sock.list():
    print db
    sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/common'%(host, port))
    uid = sock.login(db, user, pwd)

