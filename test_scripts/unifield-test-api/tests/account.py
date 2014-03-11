#!/usr/bin/env python
# -*- coding: utf8 -*-
from unifield_test import UnifieldTest

class AccountTest(UnifieldTest):

    def __init__(self, *args, **kwargs):
        '''Include some data in the database'''
        super(AccountTest, self).__init__(*args, **kwargs)
        # Values
        vals = {
            'name': 'test-20',
            'code': 'TT20',
            'type': 'other'
        }
        # Search user_type
        user_type_ids = self.p1.get('account.account.type').search([('name', '=', 'Expense')])
        vals.update({'user_type': user_type_ids[0]})
        res = self.p1.get('account.account').create(vals)

    @classmethod
    def tearDownClass(self):
        '''
        Clear data after tests have been used
        '''
        account_obj = self.p1.get('account.account')
        a_ids = account_obj.search([('name', '=', 'test-20'), ('code', '=', 'TT20')])
        account_obj.unlink(a_ids)
        super(AccountTest, self).tearDownClass()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: