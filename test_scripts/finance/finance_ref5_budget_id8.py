#!/usr/bin/env python
#-*- encoding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2014 TeMPO Consulting. All Rights Reserved
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

#####
## NEED
###

"""
For this script to work you need some existing budget.
"""

#####
## IMPORT
###
import sys
import oerplib
from datetime import datetime

#####
## VARIABLES
###
dbname='ref5_tests'
login = 'admin'
pwd = 'admin'
timeout = 3600
budget_id = 8

#####
## BEGIN
###
# Prepare the connection to the OpenERP server
o = oerplib.OERP('localhost', protocol='xmlrpc', port=8069, timeout=timeout)
# Then user
u = o.login(login, pwd, dbname)

# Select some register lines
#l_obj = o.get('msf.budget.line')
#l_ids = l_obj.search([('budget_id', '=', budget_id)])
b_obj = o.get('msf.budget')
print "Budget ID:", budget_id
before = datetime.today()
try:
  b_obj.button_display_type2([8])
except Exception, e:
  print e
finally:
  after = datetime.today()
  print str(after - before)

#####
## END
###
sys.exit(0)
