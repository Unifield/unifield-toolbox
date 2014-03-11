#!/usr/bin/env python
# -*- coding: utf8 -*-
from account import AccountTest

class AccountAccountTest(AccountTest):

    def test_010_coa(self):
        '''Check Chart of Account length'''
        db = self.db.get('project')
        ids = db.get('account.account').search([])
        self.assert_(len(ids) == 342, "Chart of Account length: %s" % len(ids))

def get_test_class():
    '''Return the class to use for tests'''
    return AccountAccountTest

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: