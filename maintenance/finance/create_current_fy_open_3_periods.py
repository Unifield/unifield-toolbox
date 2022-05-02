#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import argparse
import oerplib
import datetime
import os
from dateutil.relativedelta import relativedelta

protocol='netrpc'

parser = argparse.ArgumentParser()
parser.add_argument("--host", "-H", metavar="host", default="127.0.0.1", help="Host [default: %(default)s]")
parser.add_argument("--port", "-p", metavar="port", default=os.getenv('NETRPCPORT',8070), help="NetRPC Port [default: 8070]")
parser.add_argument("--user", "-u", metavar="user", default="admin", help="User [default: %(default)s]")
parser.add_argument("--password", "-w", metavar="pwd", default=os.getenv('ADMINPASSWORD','Only4RB'), help="Password [default: %(default)s]")

o = parser.parse_args()

login = o.user
pwd = o.password
host = o.host
port = o.port

oerp = oerplib.OERP(host, protocol=protocol, port=port, version='6.0')
for dbname in oerp.db.list():
    if 'SYNC' in dbname:
        continue
    print "Check periods on %s" % dbname
    netrpc = oerplib.OERP(host, database=dbname, protocol=protocol, port=port, timeout=1000, version='6.0')
    netrpc.login(login, pwd, dbname)
    fy_wiz_obj = netrpc.get('account.period.create')
    wiz_id = fy_wiz_obj.create({})
    fy_wiz_obj.account_period_create_periods([wiz_id])

    to_date = datetime.datetime.now() + relativedelta(day=1, months=3)
    period_obj = netrpc.get('account.period')
    to_open_ids = period_obj.search([('special', '=', False), ('date_start', '>=', '%s-01-01' % (datetime.datetime.now().strftime('%Y'), )), ('date_stop', '<=', to_date.strftime('%Y-%m-%d')), ('state', '=', 'created')])
    if to_open_ids:
        period_obj.action_open_period(to_open_ids)
        print '%s: %d periods opened' % (dbname, len(to_open_ids))
