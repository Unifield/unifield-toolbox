#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import argparse
import xmlrpc.client
import os

parser = argparse.ArgumentParser()
parser.add_argument("--host", "-H", metavar="host", default="127.0.0.1", help="Host [default: %(default)s]")
parser.add_argument("--port", "-p", metavar="port", default=os.getenv('XMLRPCPORT',8069), help="XmlRPC Port [default: %(default)s]")
parser.add_argument("--user", "-u", metavar="user", default="admin", help="User [default: %(default)s]")
parser.add_argument("--password", "-w", metavar="pwd", default=os.getenv('ADMINPASSWORD','admin'), help="Password [default: %(default)s]")

o = parser.parse_args()

login = o.user
pwd = o.password
host = o.host
port = o.port

sock = xmlrpc.client.ServerProxy('http://%s:%s/xmlrpc/db'%(host, port))
dbs = sock.list()

transport = xmlrpc.client.Transport()
connection = transport.make_connection(host)
connection.timeout = 10000

for dbname in sock.list():
    if 'SYNC' in dbname:
        continue
    print("Sync %s" % dbname)
    sock = xmlrpc.client.ServerProxy('http://%s:%s/xmlrpc/common' % (host, port))
    uid = sock.login(dbname, login, pwd)
    sock = xmlrpc.client.ServerProxy('http://%s:%s/xmlrpc/object' % (host, port), transport=transport)
    sock.execute(dbname, uid, pwd, 'sync.client.entity', 'sync')

