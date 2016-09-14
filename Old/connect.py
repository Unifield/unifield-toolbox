# -*- encoding: utf-8 -*-
import xmlrpclib
import csv
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

sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/db'%(host, port))
for db in sock.list():
    print db
    sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/common'%(host, port))
    uid = sock.login(db, user, pwd)

