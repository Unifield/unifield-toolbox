#-*- coding: utf-8 -*-
import oerplib
import unittest
import time

DB_SUFFIX = 'uf_2304_'
PARTNER_SUFFIX = 'uf_2304_'

# Connect database on sync. engine
def connect_to_sync(conn):
    """
    Connect database on sync. engine
    """
    sync_client = conn.get('sync.client.sync_server_connection')
    sync_client.action_connect([1])


class XMLRPCConnection(oerplib.OERP):

        def get_object(self):
            self.ana_acc       = self.get('account.analytic.account')
            self.distrib       = self.get('analytic.distribution')
            self.cc_dl         = self.get('cost.center.distribution.line')
            self.partner       = self.get('res.partner')
            self.addr          = self.get('res.partner.address')
            self.location      = self.get('stock.location')
            self.purchase      = self.get('purchase.order')
            self.po_line       = self.get('purchase.order.line')
            self.product       = self.get('product.product')
            self.sync_mgr      = self.get('sync.client.sync_manager')
            self.sale          = self.get('sale.order')
            self.sale_line     = self.get('sale.order.line')
            self.ssolw         = self.get('split.sale.order.line.wizard')
            self.sourcing_line = self.get('sourcing.line')
            self.poca          = self.get('procurement.order.compute.all')
            self.lot           = self.get('stock.production.lot')
            self.msw           = self.get('multiple.sourcing.wizard')


class UF2304SyncTestCase(unittest.TestCase):

    def setUp(self):
        # Project
        self.p = XMLRPCConnection('localhost', protocol='xmlrpc', port=8069)
        self.p_user = self.p.login('admin', 'admin', '%sPROJECT_01' % DB_SUFFIX)
        self.p.get_object()
        connect_to_sync(self.p)

        # Coordo
        self.c = XMLRPCConnection('localhost', protocol='xmlrpc', port=8069)
        self.c_user = self.c.login('admin', 'admin', '%sCOORDO_01' % DB_SUFFIX)
        self.c.get_object()
        connect_to_sync(self.c)

    def runTest(self):
        p = self.p
        c = self.c

        products = ['ADAPCABL1S-',
                    'ADAPCABL2S-',
                    'ADAPCART02-',
                    'DINJCEFA1V-',
                    'DORADIDA15T']
        supplier = 'ITCompany'
        int_location = 'LOG'

        p_product_ids = p.product.search([('default_code', 'in', products)])
        self.assert_(len(p_product_ids) == 5, 'Not all products found in Project !')

        c_product_ids = p.product.search([('default_code', 'in', products)])
        self.assert_(len(c_product_ids) == 5, 'Not all products found in Coordo !')

        supplier_ids = c.partner.search([('name', '=', supplier)])
        self.assert_(supplier_ids, 'ITCompany partner not found in Coordo')

        int_location_ids = p.location.search([('name', '=', int_location)])
        self.assert_(int_location_ids, 'Location %s not found in Coordo' % int_location)

        ops_ids = p.ana_acc.search([('code', '=', 'OPS')])
        self.assert_(ops_ids, 'OPS analytic account not found !')
        
        ht101_ids = p.ana_acc.search([('code', '=', 'HT101')])
        self.assert_(ht101_ids, 'HT101 analytic account not found !')

        # Creation of the analytic distribution
        ad_id = p.distrib.create({'name': 'Test DPO sync'})
        self.assert_(ad_id, 'Analytic distribution not created !')
        # Create a line in the AD
        p.cc_dl.create({'name': 'CC Line 1',
                        'amount': 0.00,
                        'percentage': 100.00,
                        'currency_id': 1,
                        'analytic_id': ops_ids[0],
                        'distribution_id': ad_id,
                        'destination_id': ht101_ids[0]})

        # Create an Internal Request
        ir_vals = {
                'location_requestor_id': int_location_ids[0],
                'delivery_requested_date': time.strftime('%Y-%m-28'),
                'procurement_request': True,
                }
        ir_id = p.sale.create(ir_vals)

        # Add a line in IR per product
        for p_product_id in p_product_ids:
            line_vals = {
                    'product_id': p_product_id,
                    'product_uom': 1,
                    'product_uom_qty': 50.00,
                    'cost_price': 1.00,
                    'order_id': ir_id,
                    }
            p.sale_line.create(line_vals)


        # Validate the IR
        p.exec_workflow('sale.order', 'procurement_validate', ir_id)
        i = 0
        ir_state = p.sale.read(ir_id, ['state'])['state']
        while ir_state != 'validated':
            time.sleep(0.5)
            ir_state = p.sale.read(ir_id, ['state'])['state']
            i += 1
            if i > 30:
                break

        self.assert_(ir_state == 'validated', 'The IR is not in Validated state !')

        # Source all lines to the COORDO
        coordo_ids = p.partner.search([('name', '=', '%sCOORDO_01' % PARTNER_SUFFIX)])
        self.assert_(coordo_ids, 'No partner %sCOORDO_01 found in %s' % (PARTNER_SUFFIX, p.database))
        
        # Get all OST line form the IR
        ost_ids = p.sourcing_line.search([('sale_order_id', '=', ir_id)])
        self.assert_(len(ost_ids) == 5, 'Not all OST lines found !')

        # Launch the multiple lines sourcing wizard
        mlsw_id = p.create('multiple.sourcing.wizard',
                           {'type': 'make_to_order',
                            'po_cft': 'po',
                            'supplier': coordo_ids[0],
                            'line_ids': [(6, 0, ost_ids)],
                           }, context={'active_ids': ost_ids})
        p.msw.save_source_lines([mlsw_id])

        # Run the scheduler
        ir_vals =  p.sale.read(ir_id, ['state', 'name'])
        ir_name = ir_vals['name']
        ir_state = ir_vals['state']
        i = 0
        while ir_state != 'progress':
            time.sleep(1)
            ir_state =  p.sale.read(ir_id, ['state'])['state']
            i += 1
            if i > 30:
                break

        self.assert_(ir_state == 'progress', 'The IR is not confirmed !')

        proc_id = p.poca.create({})
        p.execute('procurement.order.compute.all', 'procure_calculation', [proc_id])

        po_ids = p.purchase.search([('origin', 'like', ir_name)])
        i = 0
        while not po_ids:
            time.sleep(1)
            po_ids = p.purchase.search([('origin', 'like', ir_name)])
            i += 1
            if i > 30:
                break

        self.assert_(po_ids, 'No PO found with origin like \'%s\' in PROJECT_01' % ir_name)

        # Validate the PO
        p.purchase.write(po_ids, {'delivery_confirmed_date': time.strftime('%Y-%m-%d'),
                                  'analytic_distribution_id': ad_id})
        for po_id in po_ids:
            p.exec_workflow('purchase.order', 'purchase_confirm', po_id)

        po_name = p.purchase.read(po_id, ['name'])['name']

        # Run the sync. engine
        p_sync_id = p.create('sync.client.sync_manager', {})
        p.execute('sync.client.sync_manager', 'sync', p_sync_id, {'context': {}})

        time.sleep(5)


        ##############
        # At Coordo  #
        ##############

        # Run the sync. engine
        c_sync_id = c.create('sync.client.sync_manager', {})
        c.execute('sync.client.sync_manager', 'sync', c_sync_id, {'context': {}})
        time.sleep(5)

        # Get the FO created
        partner_ids = c.partner.search([('name', '=', '%sPROJECT_01' % PARTNER_SUFFIX)])
        self.assert_(partner_ids, 'No partner %sPROJECT_01 found in %s !' % (PARTNER_SUFFIX, c.database))

        fo_ids = c.search('sale.order', [('client_order_ref', 'like', po_name)], order='id desc')
        self.assert_(fo_ids, 'No FO created at Coordo with a customer ref like %s' % po_name)

        # Cancel the first line
        fo_line_ids = c.sale_line.search([('order_id', 'in', fo_ids)])
        self.assert_(fo_line_ids, 'No FO line created at Coordo with a customer ref like %s' % po_name)
        c.sale_line.ask_order_unlink([fo_line_ids[0]])

        # Validate the new FO
        c.exec_workflow('sale.order', 'order_validated', fo_ids[0])

        # Run the sync. engine at coordo
        c.execute('sync.client.sync_manager', 'sync', c_sync_id, {'context': {}})
        
        # Run the sync. engine at project
        p.execute('sync.client.sync_manager', 'sync', p_sync_id, {'context': {}})

        # Check if the line has been removed on the PO at Project side
        pol_ids = p.po_line.search([('order_id', 'in', po_ids)])
        self.assert_(len(pol_ids) == 4, 'The line has not been removed on the PO at project side.')

        # Check if the line has been removed on the IR
        irl_ids = p.sale_line.search([('order_id', '=', ir_id)])
        self.assert_(len(irl_ids) == 4, 'The line has not been removed on the IR at project side.')

        # Cancel the second line
        c.sale_line.ask_order_unlink([fo_line_ids[1]])

        # Confirm the FO
        c_ost_ids = c.sourcing_line.search([])
        self.assert_(c_ost_ids, 'No OST line found in Coordo.')
        # Launch the multiple lines sourcing wizard
        mlsw_id = c.create('multiple.sourcing.wizard',
                           {'type': 'make_to_order',
                            'po_cft': 'po',
                            'supplier': supplier_ids,
                            'line_ids': [(6, 0, c_ost_ids)],
                           }, context={'active_ids': c_ost_ids})
        c.msw.save_source_lines([mlsw_id])

        # Run the scheduler
        fo_vals =  c.sale.read(fo_ids[0], ['state', 'name'])
        fo_name = fo_vals['name']
        fo_state = fo_vals['state']
        i = 0
        while fo_state != 'done':
            time.sleep(1)
            fo_state =  c.sale.read(fo_ids[0], ['state'])['state']
            i += 1
            if i > 10:
                break

        self.assert_(fo_state == 'done', 'The FO is not confirmed !')

        fo_split_ids = c.sale.search([('name', '=', '%s-3' % fo_name)])
        self.assert_(fo_split_ids, 'No FO split found − May the FO was not split well !')

         # Run the sync. engine at coordo
        c.execute('sync.client.sync_manager', 'sync', c_sync_id, {'context': {}})

        # Run the sync. engine at project
        p.execute('sync.client.sync_manager', 'sync', p_sync_id, {'context': {}})

        po_ids = p.purchase.search([('name', '=', '%s-3' % po_name)])
        # Check if the line has been removed on the PO at Project side
        pol_ids = p.po_line.search([('order_id', 'in', po_ids)])
        self.assert_(len(pol_ids) == 3, 'The line has not been removed on the PO at project side.')

        # Check if the line has been removed on the IR
        irl_ids = p.sale_line.search([('order_id', '=', ir_id)])
        self.assert_(len(irl_ids) == 3, 'The line has not been removed on the IR at project side.')

if __name__ == '__main__':
    unittest.main()