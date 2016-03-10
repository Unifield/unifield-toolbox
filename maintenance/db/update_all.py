# -*- encoding: utf-8 -*-
import argparse
import oerplib

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--host", "-H", metavar="host", default="127.0.0.1", help="Host [default: %(default)s]")
parser.add_argument("--port", "-p", metavar="port", default=None, help="HTTP/XMLRPC Port [default: 8061/8069 (depending on protocol used)]")
parser.add_argument("--user", "-u", metavar="user", default="admin", help="User [default: %(default)s]")
parser.add_argument("--password", "-w", metavar="pwd", default="admin", help="Password [default: %(default)s]")
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

oerp = oerplib.OERP(host, protocol='xmlrpc', port=port)
for db in oerp.db.list():
    user = oerp.login(user, pwd, db)
    mod_obj = oerp.get('ir.module.module')
    mod_ids = mod_obj.search([('name', '=', 'base')])
    mod_obj.button_upgrade(mod_ids)
    bmu = oerp.get('base.module.upgrade').upgrade_module([])
