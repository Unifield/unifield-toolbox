# -*- encoding: utf-8 -*-
import xmlrpclib

dbname='jfb-wm2'
user='admin'
pwd = 'admin'
port = 7069

sock = xmlrpclib.ServerProxy('http://127.0.0.1:%s/xmlrpc/common'%(port, ))
uid = sock.login(dbname, user, pwd)
sock = xmlrpclib.ServerProxy('http://127.0.0.1:%s/xmlrpc/object'%(port, ))

model = 'base.update.translations'
ids = sock.execute(dbname, uid, pwd, model, 'create', {'lang': 'en_US'})
sock.execute(dbname, uid, pwd, model, 'act_update', [ids])
