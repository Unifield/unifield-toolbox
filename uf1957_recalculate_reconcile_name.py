#!/usr/bin/env python
#-*- encoding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2013 TeMPO Consulting. All Rights Reserved
#    TeMPO Consulting (<http://www.tempo-consulting.fr/>).
#    Author: Olivier DOSSMANN
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import xmlrpclib
import os
import sys

# Prepare some values

dbname='MC_OCG_KG_COO'
user='admin'
pwd = 'admin'
sock = xmlrpclib.ServerProxy('http://127.0.0.1:8069/xmlrpc/common')
try:
  uid = sock.login(dbname, user, pwd)
except Exception, e:
  print e
  sys.exit(1)
sock = xmlrpclib.ServerProxy('http://127.0.0.1:8069/xmlrpc/object')
sock_wiz = xmlrpclib.ServerProxy('http://127.0.0.1:8069/xmlrpc/wizard')

# Models
ml_model = 'account.move.line'

# Methods
def give_reconciliation_name(ids, field):
  if not ids or not field:
    return False
  # Browse entries
  for line in sock.execute(dbname, uid, pwd, ml_model, 'read', ids, [field, 'reconcile_txt']):
    reconcile_id = line.get(field) and line.get(field)[0] or False
    if reconcile_id:
      name = line.get(field) and line.get(field)[1] or ''
      if not name:
        print "WRONG:", line.get('id'), "no NAME"
        continue
      print "Writing line", line.get('id'), ":", name
      # NB: in order Unifield to take count of 'reconcile_txt' field, we should add 'reconcile_id' too (condition for reconcile_txt to be accepted/rebuild)
      sock.execute(dbname, uid, pwd, ml_model, 'write', line.get('id'), {'reconcile_txt': name, field: reconcile_id})
    else:
      print "WRONG:", line.get('id'), "no reconcile ID"

# Search non reconciled lines but with 'reconcile_txt' empty field
reconcile_ids = sock.execute(dbname, uid, pwd, ml_model, 'search', [('reconcile_txt', '=', ''), ('reconcile_id', '!=', False)])
partial_ids = sock.execute(dbname, uid, pwd, ml_model, 'search', [('reconcile_txt', '=', ''), ('reconcile_partial_id', '!=', False)])

# Do total reconciliation process
if not reconcile_ids:
  print "INFO:", "Total reconciliation are OK."
else:
  give_reconciliation_name(reconcile_ids, 'reconcile_id')
# Do partial reconciliation process
if not partial_ids:
  print "INFO:", "Partial reconciliation are OK."
else:
  give_reconciliation_name(partial_ids, 'reconcile_partial_id')

# quit script
sys.exit(0)
