#!/usr/bin/env python
# -*- coding: utf8 -*-
from test_01 import SomethingTest
import unittest

class AnotherTest(SomethingTest):

    ###########################################################################
    ## We skip test_020 because it was already done in SomethingTest class.
    ## We consider that test_020 should not be executed twice (or more)
    ###########################################################################
    @unittest.skip('Already used')
    def test_020_sentence(self):
        super(AnotherTest.test_020_sentence())

    def test_030_after(self):
        '''Method used after all others methods'''
        print "Third test method"

def get_test_class():
    '''Return the class to use for tests'''
    return AnotherTest

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: