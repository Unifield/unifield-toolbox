#!/usr/bin/env python

import psycopg2
import re
from datetime import datetime
from dateutil.relativedelta import relativedelta

decom = {}
db = psycopg2.connect(dbname='prod_SYNC_SERVER_LOCAL')
cr = db.cursor()
cr.execute("select name from sync_server_entity where state='invalidated';")

re_prefix = ['prod_', 'oc.-uf_', 'oc._', 'oc.-dbs_', 'oc.-usdb_']
for inv in cr.fetchall():
    decom[inv[0]] = True



to_del_decom = []

db = psycopg2.connect(dbname='template1')
cr = db.cursor()


cr.execute('SELECT d.datname,pg_get_userbyid(d.datdba) FROM pg_catalog.pg_database d')
all_db_by_user = {}
junk = []

for db, user in cr.fetchall():
    db_match = re.match('^(.*)_([0-9]{8})_([0-9]{4})(_[0-9]*)?$', db)
    if db_match:
        if db_match.group(4):
            junk.append(db)
        else:
            db_prefix = db_match.group(1)
            instance_name = db_prefix
            for pr in re_prefix:
                instance_name = re.sub('^%s'%pr, '', instance_name)
            if instance_name in decom:
                if datetime.strptime(db_match.group(2), '%Y%m%d') + relativedelta(months=+3) < datetime.now():
                    to_del_decom.append(db)
            all_db_by_user.setdefault(user, {}).setdefault(db_prefix, []).append(db)

for user in all_db_by_user:
    for db in all_db_by_user[user]:
        if len(all_db_by_user[user][db]) > 1:
            sorted_db = sorted(all_db_by_user[user][db])
            sorted_db.pop()
            junk += sorted_db


for to_del in junk:
    print('duplicate dropdb %s' % to_del)

if to_del_decom:
    print('decom dropdb: %s' % (' '.join(to_del_decom), ))

if junk:
    cr.execute('select pid, usename, application_name, datname from pg_stat_activity where datname in %s', (tuple(junk),))
    for x in cr.fetchall():
        print(x)
