'''
Created on Feb 28, 2014

@author: qt
'''
import unittest

from unifield_xmlrpc import XMLRPCConnection as XMLConn


class UnifieldTest(unittest.TestCase):

    def setUp(self):
        self.sync_db = XMLConn('SYNC_SERVER')
        self.hq1 = XMLConn('HQ1')
        self.c1 = XMLConn('C1')
        self.c1p1 = XMLConn('C1P1')
        super(UnifieldTest, self).setUp()


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
