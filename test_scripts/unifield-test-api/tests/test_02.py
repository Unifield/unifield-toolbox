import test_01

class AnotherTest(test_01.SomethingTest):

    def test_030_after(self):
        '''Method used after all others methods'''
        print "Third test method"

def get_test_class():
    '''Return the class to use for tests'''
    return AnotherTest