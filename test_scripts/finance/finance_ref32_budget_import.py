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
For this script to work you need a register line template file which filename is "import_budget_mw109_template.csv"
"""

#####
## IMPORT
###
import sys
import oerplib
from datetime import datetime
from base64 import encodestring

#####
## VARIABLES
###
dbname='ref32'
login = 'admin'
pwd = 'admin'
timeout = 3600
# Prepare filename
fileurl = '/home/olivier/projets/Unifield/z_scripts/refactoring/import_budget_mw102_template.csv'

#####
## BEGIN
###
# Prepare the connection to the OpenERP server
o = oerplib.OERP('localhost', protocol='xmlrpc', port=8069, timeout=timeout)
# Then user
u = o.login(login, pwd, dbname)

# Create wizard
wiz_obj = o.get('wizard.budget.import')
res_id = wiz_obj.create({'import_file': encodestring(open(fileurl, 'r').read())}, {})
print "Wizard created. ID:", res_id
before = datetime.today()
try:
#  wiz_obj.import_csv_budget([res_id]) # Normal behaviour (BEFORE refactoring)
#  wiz_obj.call_import([res_id]) # Behaviour to use RunSnakeRun
  wiz_obj.button_import([res_id]) # AFTER refactoring
except Exception, e:
  print e
finally:
  after = datetime.today()
  print str(after - before)

#####
## END
###
sys.exit(0)
