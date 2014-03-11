#!/usr/bin/env python
# -*- coding: utf8 -*-
import unittest

class SomethingTest(unittest.TestCase):

    def unused_method(self):
        '''Test that nothing is printed in this method because we shouldn't go into!'''
        print "Unused method is... used!"

    def test_010_list(self):
        '''Test that list works'''
        a = [0, 1, 2]
        self.assert_(len(a) == 3, "List should be 3 instead of %s" % (len(a)))

    def test_020_sentence(self):
        '''Test that a sentence is not the same as another'''
        s1 = "Something wrong"
        s2 = "Or not!"
        self.assert_(s1 != s2, "Same sentence? Incredible!")

def get_test_class():
    '''Return the class to use for tests'''
    return SomethingTest

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: