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
                # Values
                vals = {
                    'name': 'test-20',
                    'code': 'TT20',
                    'type': 'other'
                }
                # Search user_type
                user_type_ids = database.get('account.account.type').search([('name', '=', 'Expense')])
                vals.update({'user_type': user_type_ids[0]})
                database.get('account.account').create(vals)
                # Write the fact that the data have been loaded
                database.get(self.test_module_obj_name).create({'name': keyword, 'active': True})
            else:
                print "%s exists!" % (keyword)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: