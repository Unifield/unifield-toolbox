#!/usr/bin/env python

import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
import ConfigParser
import base64
import getpass


dbnames = []

if len(sys.argv) == 1:
    print('%s list,of,dbs' % sys.argv[0])
    sys.exit(1)

if len(sys.argv) > 2:
    target_user = sys.argv[2]
else:
    target_user = getpass.getuser()

db2 = psycopg2.connect(dbname='template1')
db2.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cr2 = db2.cursor()

# parse openrc to get xmlrpc port, password, sync db ...
sync_port = False
sync_db = '%s_SYNC_SERVER_LOCAL' % target_user
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

    cr2.execute("SELECT d.datname FROM pg_catalog.pg_database d WHERE pg_get_userbyid(d.datdba) = %s and d.datname like '%%SYNC_SERVER%%'", (target_user, ))
    for xx in cr2.fetchall():
        sync_db = xx[0]

# search dbs to duplicate
for pattern_db in sys.argv[1].split(','):
    cr2.execute("SELECT d.datname FROM pg_catalog.pg_database d WHERE pg_get_userbyid(d.datdba) = 'production-dbs' and d.datname ilike '%%%s%%' order by d.datname" % pattern_db)
    for db in cr2.fetchall():
        dbnames.append(db[0])
        if 'SYNC' in db[0]:
            sync_db = '%s_%s' % (target_user, db[0][5:])

if not dbnames:
    print('No db found')
    sys.exit(1)


ret = ' '
print('Sync user: %s, sync db: %s, sync port: %s, user password: %s' % (sync_user, sync_db, sync_port, user_pass))
print('DB Found: %s' %(', '.join(dbnames)))
while ret.lower() not in ('', 'y', 'n'):
    ret = raw_input("Duplicate ? [Y/n] ")
if ret.lower() == 'n':
    sys.exit(1)


# createdb -T
for dbname in dbnames:
    try:
        cr2.execute('REVOKE CONNECT ON DATABASE "%s" FROM public' % dbname)
        cr2.execute('select pid from pg_stat_activity where datname = %s', (dbname, ))
        for x in cr2.fetchall():
            print('Kill connection %s' % x[0])
            cr2.execute('select pg_terminate_backend(%s)' % x[0])

        new_dbname = '%s_%s' % (target_user, dbname[5:])
        print('Copy %s to %s' % (dbname, new_dbname))
        cr2.execute('create database "%s" template="%s"' % (new_dbname, dbname))
    except Exception, e:
        print('Unable to duplicate %s: %s' % (dbname, e))
        continue
    finally:
        cr2.execute('GRANT CONNECT ON DATABASE "%s" TO public' % dbname)

    db1 = psycopg2.connect(dbname=new_dbname)
    cr1 = db1.cursor()

    cr1.execute('alter database "%s" owner to "%s"' % (new_dbname, target_user))
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


    if sync_port and sync_db:
        cr1.execute("update sync_client_sync_server_connection set host='127.0.0.1', protocol='xmlrpc', port=%s, database=%s, login=%s", (sync_port, sync_db, sync_user))
    else:
        print('Unable to set sync_client_sync_server_connection')

    if user_pass:
        cr1.execute("update res_users set password=%s", (user_pass,))
    else:
        print('Passwords not changed')


    db1.commit()

cr2.close()
