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
    @var sync: contains Synchro Server oerplib connection
    @var hq1: same as sync for HQ1 DB
    @var c1: same as sync for HQ1C1 DB
    @var p1: same as sync for HQ1C1P1 DB
    @var db: contains the list of DB connections
    '''
    db = {}

    def _addConnection(self, db_suffix, name):
        '''
        Add new connection
        '''
        con = XMLConn(db_suffix)
        setattr(self, name, con)
        self.db[name] = con

    def __init__(self, *args, **kwargs):
        super(UnifieldTest, self).__init__(*args, **kwargs)
        # Keep each database connection
        self._addConnection('SYNC_SERVER', 'sync')
        self._addConnection('HQ1', 'hq1')
        self._addConnection('HQ1C1', 'c1')
        self._addConnection('HQ1C1P1', 'p1')
        # For each database, check that unifield_tests module is loaded
        #+ If not, load it.
        module_to_install = 'unifield_tests'
        for database_name in self.db:
            database = self.db.get(database_name)
            module_obj = database.get('ir.module.module')
            m_ids = module_obj.search([('name', '=', module_to_install)])
            for module in module_obj.read(m_ids, ['state']):
                state = module.get('state', '')
                if state == 'uninstalled':
                    print ('Updating %s module for %s DB' % (module_to_install, database_name))
                    module_obj.button_install([module.get('id')])
                    database.get('base.module.upgrade').upgrade_module([])
                elif state in ['to upgrade', 'to install']:
                    print ('Updating %s module for %s DB' % (module_to_install, database_name))
                    database.get('base.module.upgrade').upgrade_module([])
                elif state in ['installed']:
                    print ('%s module already installed in %s DB' % (module_to_install, database_name))
                    pass
                else:
                    raise EnvironmentError('Wrong module state: %s' % (state or '',))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: