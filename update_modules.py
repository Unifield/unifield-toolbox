#!/usr/bin/python
# -*- encoding: utf-8 -*-
import xmlrpclib
import sys


dbs = [('finance','admin'), ('supply','admin'), ('sprint1', 'admin'), ('sandbox', 'admin')]
user = "admin"
host = "127.0.0.1"
port = "8069"
#port = "8062"

if len(sys.argv) < 2:
    print "Usage: %s module1,module2,...."%(sys.argv[0],)
    sys.exit(1)

modules = sys.argv[1].split(',')
ok = True
for dbname,pwd in dbs:
    sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/common'%(host,port))
    uid = sock.login(dbname, user, pwd)
    sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object'%(host,port))

    ids = sock.execute(dbname, uid, pwd, 'ir.module.module', 'search',[('name', 'in', modules),('state','in',['installed', 'to upgrade'])])
    if len(ids) != len(modules):
        print "Base: %s, modules not present"%(dbname,)
        ok = False

if not ok:
    sys.exit(1)

for dbname,pwd in dbs:
    sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/common'%(host,port))
    uid = sock.login(dbname, user, pwd)
    sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object'%(host,port))

    ids = sock.execute(dbname, uid, pwd, 'ir.module.module', 'search',[('name', 'in', modules),('state','=','installed')])
    sock.execute(dbname, uid, pwd, 'ir.module.module', 'button_upgrade', ids)

    sock.execute(dbname, uid, pwd, 'base.module.upgrade', 'upgrade_module', [])
