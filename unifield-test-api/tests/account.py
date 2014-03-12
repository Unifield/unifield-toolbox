#!/usr/bin/env python
# -*- coding: utf8 -*-
from unifield_test import UnifieldTest

class AccountTest(UnifieldTest):

    def __init__(self, *args, **kwargs):
        '''
        Include some account data in the database.
        Include/create them only if they have not been already created.
        To know this, we use the key: "account_test_class"
        '''
        super(AccountTest, self).__init__(*args, **kwargs)
        keyword = 'account_test_class'
        for database_name in self.db:
            database = self.db.get(database_name)
            # If no one, create a test account
            if not self.is_keyword_present(database, keyword):
                pass
#                 # 00 prepare some values
#                 account_type_obj = database.get('account.account.type')
#                 account_obj = database.get('account.account')
#                 company_id = database.get('res.users').read(1, ['company_id']).get('company_id')
#                 # 01 Create some account type
#                 # receivable type
#                 database.account_account_type_receivable0 = account_type_obj.create({
#                     'close_method': 'balance',
#                     'code': 'receivable',
#                     'name': 'Receivable',
#                     'sign': 1
#                 })
#                 # expense type
#                 database.account_account_type_expense0 = account_type_obj.create({
#                     'close_method': 'unreconciled',
#                     'code': 'expense',
#                     'name': 'Expense',
#                     'sign': 1,
#                 })
#                 # transfer type
#                 database.account_account_type_transfer0 = account_type_obj.create({
#                     'close_method': 'balance',
#                     'code': 'transfer',
#                     'name': 'Transfer',
#                     'sign': 1,
#                     'report_type': 'asset'
#                 })
#                 # cash type
#                 database.account_account_type_cash0 = account_type_obj.create({
#                     'close_method': 'balance',
#                     'code': 'cash',
#                     'name': 'Cash',
#                     'sign': 1,
#                     'report_type': 'asset',
#                 })
#                 # 02 Create some accounts using previous account type
#                 # payable account
#                 database.account_account_payable0 = account_obj.create({
#                     'code': '401-supplier-test',
#                     'company_id': company_id,
#                 })
#                 # Values
#                 vals = {
#                     'name': 'cash account',
#                     'code': 'cash_accou',
#                     'type': 'other'
#                 }
#                 # Search user_type
#                 user_type_ids = database.get('account.account.type').search([('name', '=', 'Expense')])
#                 vals.update({'user_type': user_type_ids[0]})
#                 database.get('account.account').create(vals)
#                 # Write the fact that the data have been loaded
#                 database.get(self.test_module_obj_name).create({'name': keyword, 'active': True})
            else:
                print "%s exists!" % (keyword)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: