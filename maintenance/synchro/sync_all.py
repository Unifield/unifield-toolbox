# -*- encoding: utf-8 -*-
import argparse
import oerplib

protocol='netrpc'

parser = argparse.ArgumentParser()
parser.add_argument("--host", "-H", metavar="host", default="127.0.0.1", help="Host [default: %(default)s]")
parser.add_argument("--port", "-p", metavar="port", default=8070, help="NetRPC Port [default: 8070]")
parser.add_argument("--user", "-u", metavar="user", default="admin", help="User [default: %(default)s]")
parser.add_argument("--password", "-w", metavar="pwd", default="admin", help="Password [default: %(default)s]")

o = parser.parse_args()

login = o.user
pwd = o.password
host = o.host
port = o.port

oerp = oerplib.OERP(host, protocol=protocol, port=port, version='6.0')
for dbname in oerp.db.list():
    if 'SYNC' in dbname:
        continue
    print "Sync %s" % dbname
    netrpc = oerplib.OERP(host, database=dbname, protocol=protocol, port=port, timeout=1000, version='6.0')
    netrpc.login(login, pwd, dbname)
    conn_manager = netrpc.get('sync.client.sync_server_connection')
    conn_ids = conn_manager.search([])
    #conn_manager.write(conn_ids, {'password': login})
    conn_manager.connect()
    netrpc.get('sync.client.entity').sync()

