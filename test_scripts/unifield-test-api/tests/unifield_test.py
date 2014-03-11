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
        # Keep each database connection
        self.sync = XMLConn('SYNC_SERVER')
        self.hq1 = XMLConn('HQ1')
        self.c1 = XMLConn('HQ1C1')
        self.p1 = XMLConn('HQ1C1P1')
        # For each database, check that unifield_tests module is loaded
        #+ If not, load it.
        module_to_install = 'unifield_tests'
        for database_name in ['hq1', 'c1', 'p1']:
            database = getattr(self, database_name)
            module_obj = database.get('ir.module.module')
            m_ids = module_obj.search([('name', '=', module_to_install)])
            for module in module_obj.read(m_ids, ['state']):
                state = module.get('state', '')
                if state == 'uninstalled':
                    module_obj.button_install(module.get('id'))
                    database.get('base.module.upgrade').upgrade_module([])
                elif state in ['to upgrade', 'to install']:
                    database.get('base.module.upgrade').upgrade_module([])
                elif state in ['installed']:
                    pass
                else:
                    raise EnvironmentError('Wrong module state: %s' % (state or '',))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: