'''
Created on Feb 28, 2014

@author: qt
'''
import unittest
from tests_config.unifield_test import UnifieldTest

class IncomingShipmentTest(UnifieldTest):
    """
    This TestCase will check if all needed data are present in the
    database.
    """

    def checkProducts(self):
        """
        Check if all needed data are present in the DB. If not create it.
        """


    def setUp(self):
        super(IncomingShipmentTest, self).setUp()

    def tearDown(self):
        pass


    def testName(self):
        pass


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
