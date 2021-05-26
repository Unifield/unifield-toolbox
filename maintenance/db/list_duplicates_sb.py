#!/usr/bin/env python

import psycopg2
import re

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
            all_db_by_user.setdefault(user, {}).setdefault(db_prefix, []).append(db)

for user in all_db_by_user:
    for db in all_db_by_user[user]:
        if len(all_db_by_user[user][db]) > 1:
            sorted_db = sorted(all_db_by_user[user][db])
            sorted_db.pop()
            junk += sorted_db

for to_del in junk:
    print 'dropdb %s' % to_del

