#!/usr/bin/env python
# -*- coding: utf8 -*-
import unittest
from oerplib.oerp import OERP

OERP_DB = 'ref_tests'
OERP_PORT = '7070'

class AccountTest(unittest.TestCase):
    """
    account.account Unifield object tests
    """

    def __init__(self, args):
        """
        OpenERP connection initialization
        """
        o = OERP(server='localhost', database=OERP_DB, protocol='xmlrpc', port=OERP_PORT)
        u = o.login('admin', 'admin', OERP_DB)
        self.o = o
        self.u = u
        # account object creation
        self.account_obj = o.get('account.account')
        return super(AccountTest, self).__init__(args)

    def test_010_account_list(self):
        """
        Test that the database contains a list of 341 account items.
        """
        account_ids = self.account_obj.search([])
        self.assert_(account_ids != False, 'No account found!')
        self.assert_(len(account_ids) == 341, 'Should find 341 accounts. Found: %s' % (len(account_ids)))

    def test_020_account_creation_01(self):
        """
        Simple account creation
        """
        # Values
        vals = {
            'name': 'test-20',
            'code': 'TT20',
            'type': 'other'
        }
        # Search user_type
        user_type_ids = self.o.get('account.account.type').search([('name', '=', 'Expense')])
        self.assert_(user_type_ids != False, "No 'Expense' account type found!")
        vals.update({'user_type': user_type_ids[0]})
        res = self.account_obj.create(vals)
        self.assert_(res != False, 'Account creation failed.')
        # Delete previous account
        self.assert_(self.account_obj.unlink([res]) != False, 'Problem to delete account ID: %s' % (res))

if __name__ == "__main__":
    # Basic behaviour
#      unittest.main()
    # Most verbose behaviour (with name of methods and if it's OK or not)
#     suite = unittest.TestLoader().loadTestsFromTestCase(AccountTest)
#     unittest.TextTestRunner(verbosity=2).run(suite)
    # XML way (for Jenkins, CruiseControl, etc.) Cf. http://www.stevetrefethen.com/blog/publishing-python-unit-test-results-in-jenkins
#     import xmlrunner
#     unittest.main(testRunner=xmlrunner.XMLTestRunner(output='account_test-reports'))
    # HTML way
    import HTMLTestRunner
    suite = unittest.TestLoader().loadTestsFromTestCase(AccountTest)
    output = file('output.html', 'wb')
    runner = HTMLTestRunner.HTMLTestRunner(
        stream=output,
        title='Account test',
        description='account.account model tests'
    )
    runner.run(suite)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: