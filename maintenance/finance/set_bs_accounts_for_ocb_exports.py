#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script initially done in UFTP-106 (Cf. http://jira.unifield.org/browse/UFTP-106).

It aims to change all accounts (account.account object) 'shrink entries for HQ export' to False, except those accounts:
  - 10100
  - 10200
  - 10210

TODO: 
  - make the program to work with a list of account we give in argument
"""
# Libraries
from argparse import ArgumentParser
import oerplib

def main():
  # Description of usage
  current_usage = """usage: %prog -d database -p port [-w] admin_password

Set all account with a "Shrink entries for HQ export" to False, except 10100, 10200 and 10210 account.\n
This need an XMLRPC connection."""
  parser = ArgumentParser(usage=current_usage)
  parser.add_argument("--database", "-d", metavar="database", help="Database name", required=True)
  parser.add_argument("--password", "-w", metavar="pwd", default="admin", help="Password [default: %(default)s]")
  parser.add_argument("--port", "-p", metavar="port", default="8069", help="Port [default: %(default)s]", required=True)

  # Default variables
  user = 'admin'
  host = 'localhost'
  excluded_accounts = ['10100', '10200', '10210']
  field_name = 'shrink_entries_for_hq'

  opt = parser.parse_args()

  # Fetch some elements
  pwd = opt.password or 'admin'
  db = opt.database
  port = opt.port

  # Connection to the DB with oerplib library
  o = oerplib.OERP(host, protocol='xmlrpc', port=port)
  u = o.login(user, pwd, db)

  # Fetch specific accounts
  a = o.get('account.account')
  found_accounts = []
  for account in excluded_accounts:
    a_ids = a.search([('code', '=', account)])
    msg = ''
    if a_ids:
      found_accounts += a_ids
      msg = "[FOUND]"
    else:
      msg = "[NONE ]"
    msg += " %s" % account
    print(msg)

  # Set all account with "Shrink entries for HQ Entries" to False, except given account
  all_account_ids = a.search([]) # all accounts
  account_ids = [x for x in all_account_ids if x not in found_accounts] # all account except those found in found_accounts
  step1_result = a.write(account_ids, {field_name: False}) # write all account to False
  step2_result = a.write(found_accounts, {field_name: True})

  # Print result
  if step1_result:
    print("[OK] All acounts set to False")
  else:
    print("[ER] Problem setting up all accounts to False")
  if step2_result:
    print("[OK] %s accounts set to True" % excluded_accounts)
  else:
    print("[ER] Problem during set up of %s" % excluded_accounts)

if __name__ == '__main__':
  main()

