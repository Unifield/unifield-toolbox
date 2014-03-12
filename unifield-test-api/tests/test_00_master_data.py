#!/usr/bin/env python
# -*- coding: utf8 -*-
from unifield_test import UnifieldTest

class MasterData(UnifieldTest):

    def create_partner(self, db, vals, customer=False, employee=False, supplier=True, type='external'):
        '''
        Create a partner in the DB with vals.
        If not name given, create a random one with 3 letters.
        '''
        res = False
        vals.update({
            'customer': customer,
            'employee': employee,
            'supplier': supplier,
            'partner_type': type
        })
        if not vals.get('name', False):
            import random
            import string
            vals.update({'name': ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(3))})
        return db.get('res.partner').create(vals)

    def __init__(self, *args, **kwargs):
        super(MasterData, self).__init__(*args, **kwargs)
        keyword = 'master_data'
        self.master_data_keyword = keyword
        for database_name in self.db:
            database = self.db.get(database_name)
            if not self.is_keyword_present(database, keyword):
                # LAUNCH MASTER DATA CREATION
                # first some partners
                self.create_partner(database, {}, type='intermission')
                self.create_partner(database, {}, type='esc')
                self.create_partner(database, {}, type='section')
                self.create_partner(database, {}, type='internal')
                database.get(self.test_module_obj_name).create({'name': keyword, 'active': True})

    def test_010_master_data_loaded(self):
        '''
        Check that master data are loaded (just keyword must be present)
        '''
        for database_name in self.db:
            database = self.db.get(database_name)
            self.assert_(self.is_keyword_present(database, self.master_data_keyword) is True, "%s: Master data not loaded!" % (database_name))

def get_test_class():
    '''Return the class to use for tests'''
    return MasterData

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: