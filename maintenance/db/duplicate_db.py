#!/usr/bin/env python

import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
import ConfigParser
import base64
import getpass


dbname = sys.argv[1]

if len(sys.argv) > 2:
    target_user = sys.argv[2]
else:
    target_user = getpass.getuser()
    db2 = psycopg2.connect(dbname='template1')
    db2.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cr2 = db2.cursor()
    try:
        cr2.execute('REVOKE CONNECT ON DATABASE "%s" FROM public' % dbname)
        cr2.execute('select pid from pg_stat_activity where datname = %s', (dbname, ))
        for x in cr2.fetchall():
            print('Kill connection %s' % x[0])
            cr2.execute('select pg_terminate_backend(%s)' % x[0])

        print('Duplicate db %s to %s_%s' % (dbname, target_user, dbname))
        cr2.execute('create database "%s_%s" template="%s"' % (target_user, dbname, dbname))
    finally:
        cr2.execute('GRANT CONNECT ON DATABASE "%s" TO public' % dbname)
    cr2.close()

db1 = psycopg2.connect(dbname=dbname)
cr1 = db1.cursor()

cr1.execute('alter database "%s" owner to "%s"' % (dbname, target_user))
cr1.execute("select tablename from pg_tables where schemaname = 'public'")
for xx in cr1.fetchall():
    cr1.execute('alter table "%s" owner to "%s"' % (xx[0], target_user))

cr1.execute("select sequence_name from information_schema.sequences where sequence_schema = 'public'")
for xx in cr1.fetchall():
    cr1.execute('alter table "%s" owner to "%s"' % (xx[0], target_user))

cr1.execute("select table_name from information_schema.views where table_schema = 'public'")
for xx in cr1.fetchall():
    cr1.execute('alter table "%s" owner to "%s"' % (xx[0], target_user))

cr1.execute("SELECT format('%I.%I(%s)', ns.nspname, p.proname, oidvectortypes(p.proargtypes)) FROM pg_proc p INNER JOIN pg_namespace ns ON (p.pronamespace = ns.oid) WHERE ns.nspname = 'public'")
for xx in cr1.fetchall():
    cr1.execute('alter function %s owner to "%s"' % (xx[0], target_user))


sync_port = False
sync_db = False
user_pass = False
sync_user = 'sandbox_sync-user'
openrc = os.path.expanduser('~%s/etc/openerprc'%target_user)
if os.path.exists(openrc):
    try:
        p = ConfigParser.ConfigParser()
        p.read([openrc])
        sync_port = p.get('options', 'xmlrpc_port')
        if not user_pass:
            user_pass = p.get('options', 'sync_user_password')
            try:
                b64decoded = base64.decodestring(user_pass)
                b64decoded.decode('UTF-8')
                user_pass = b64decoded
            except:
                # no utf-8 password is not b64 encoded
                pass
        sync_user = p.get('options', 'sync_user_login')
    except:
        print('Unable to read %s' % openrc)

    cr1.execute("SELECT d.datname FROM pg_catalog.pg_database d WHERE pg_get_userbyid(d.datdba) = %s and d.datname like '%%SYNC_SERVER%%'", (target_user, ))
    for xx in cr1.fetchall():
        sync_db = xx[0]

if sync_port and sync_db:
    cr1.execute("update sync_client_sync_server_connection set host='127.0.0.1', port=%s, database=%s, login=%s", (sync_port, sync_db, sync_user))
else:
    print('Unable to set sync_client_sync_server_connection')

if user_pass:
    cr1.execute("update res_users set password=%s", (user_pass,))
else:
    print('Passwords not changed')


db1.commit()

