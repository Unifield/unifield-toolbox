import test_01
import unittest

class AnotherTest(test_01.SomethingTest):

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