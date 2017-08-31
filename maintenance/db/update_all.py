# -*- encoding: utf-8 -*-
import argparse
import oerplib
import socket

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--host", "-H", metavar="host", default="127.0.0.1", help="Host [default: %(default)s]")
parser.add_argument("--port", "-p", metavar="port", default=None, help="HTTP/XMLRPC Port [default: 8061/8069 (depending on protocol used)]")
parser.add_argument("--user", "-u", metavar="user", default="admin", help="User [default: %(default)s]")
parser.add_argument("--password", "-w", metavar="pwd", default="admin", help="Password [default: %(default)s]")
parser.add_argument("--exclude", "-x", metavar="exclude", default=False, help="Comma separated list of dbs to exclude")
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
if o.exclude:
    exclude = o.exclude.split(',')

if __name__ == '__main__':
    jobs = []
    oerp = oerplib.OERP(host, protocol='xmlrpc', port=port, version='6.0')
    for db in oerp.db.list():
        if db in exclude:
            continue
        uid = oerp.login(user, pwd, db)
        mod_obj = oerp.get('ir.module.module')
        mod_ids = mod_obj.search([('name', '=', 'base')])
        mod_obj.button_upgrade(mod_ids)
        try:
            oerp.get('base.module.upgrade').upgrade_module([])
        except socket.timeout:
            print 'Time Out. Go to next DB'

    print "Update DBs done"
