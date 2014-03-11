#!/usr/bin/env python
# -*- coding: utf8 -*-
'''
Created on Feb 28, 2014

@author: qt
Modified by 'od' on 2014 March, the 11th
'''
import unittest
from connection import XMLRPCConnection as XMLConn

class UnifieldTest(unittest.TestCase):
    '''
    Main test class for Unifield tests using TestCase and Openerplib as main inheritance
    @var db: contains links to databases
    '''
    db = {}
    pool = {}

    def __init__(self, *args, **kwargs):
        super(UnifieldTest, self).__init__(*args, **kwargs)
        self.sync = XMLConn('SYNC_SERVER')
        self.hq1 = XMLConn('HQ1')
        self.c1 = XMLConn('HQ1C1')
        self.p1 = XMLConn('HQ1C1P1')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: