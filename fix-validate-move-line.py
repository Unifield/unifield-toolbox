# -*- encoding: utf-8 -*-

import xmlrpclib

dbname='finance'
user='admin'
pwd = ''
sock = xmlrpclib.ServerProxy('http://127.0.0.1:8069/xmlrpc/common')
uid = sock.login(dbname, user, pwd)
sock = xmlrpclib.ServerProxy('http://127.0.0.1:8069/xmlrpc/object')
model = 'account.move'
ids = sock.execute(dbname, uid, pwd, model, 'search', [])
for move in sock.execute(dbname, uid, pwd, model, 'read',ids, ['line_id','name','ref']):
    ssum = 0
    lines = []
    if move['line_id']:
        for line in sock.execute(dbname, uid, pwd,  'account.move.line', 'read',move['line_id'], ['debit','credit','state']):
            ssum += line['debit'] - line['credit']
            lines.append(line)
    if ssum >= 0.0001:
        print 'FIX'
        sock.execute(dbname, uid, pwd,  'account.move.line', 'write', [l['id'] for l in lines], {})
