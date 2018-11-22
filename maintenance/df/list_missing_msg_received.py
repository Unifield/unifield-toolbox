#! /usr/bin/python

import psycopg2
import psycopg2.extras

dsn='dbname=jfb-us-5364_SYNC_SERVER_LIGHT_NO_MASTER'
db = psycopg2.connect(dsn)
cr = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

db2 = psycopg2.connect('dbname=jfb-us-5364_prod_OCBBI126_20181120_1931')
cr2 = db2.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cr.execute("select identifier, remote_call, arguments from sync_server_message where destination=317 and write_date>'2018-11-08 00:00:00' and write_date <'2018-11-08 23:00:00' and sent='t'");
hit = 0
miss = 0
call = {}
order = {}
for x in cr.fetchall():
    cr2.execute('select * from sync_client_message_received where identifier=%s and remote_call=%s and arguments=%s', (x['identifier'], x['remote_call'], x['arguments'] ))
    if not cr2.rowcount:
        call.setdefault(x['remote_call'], 0)
        call[x['remote_call']] +=1
        arg = eval(x['arguments'])
        o = arg[0]['order_id']['name']
        order.setdefault(o, {'total': 0, 'state': {}})
        order[o]['total'] += 1
        state = arg[0]['state']
        order[o]['state'].setdefault(state, 0)
        order[o]['state'][state] += 1
        miss += 1
    if cr2.rowcount:
        hit += 1


print 'Hit:', hit, 'Miss:', miss
print call
print order
