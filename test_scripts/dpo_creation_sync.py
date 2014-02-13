#-*- coding: utf-8 -*-
import oerplib
import unittest
import time

from oerplib import error

DB_SUFFIX = 'uf_2301_'

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
            self.sourcing_line = self.get('sourcing.line')
            self.poca          = self.get('procurement.order.compute.all')
            self.picking       = self.get('stock.picking')
            self.partial_pick  = self.get('stock.partial.picking')


class DPOSyncTestCase(unittest.TestCase):

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

    def getAnalyticDistribution(self):
        p = self.p
        c = self.c

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

        return ad_id

    def getPartners(self, partner_name):
        p = self.p
        c = self.c

        partner_ids = p.partner.search([('name', '=', partner_name)])
        self.assert_(partner_ids, 'Partner COORDO_01 not found in PROJECT_01 !')
        partner = p.partner.browse(partner_ids[0])

        # Search address for the partner COORDO_01
        addr_ids = p.addr.search([('partner_id', '=', partner_ids[0])])
        self.assert_(addr_ids, 'No address found for the partner COORDO_01 !')

        return partner, addr_ids

    def runSyncProjectCoordo(self):
        p = self.p
        c = self.c

        # Run the sync. engine at Project
        p.execute('sync.client.sync_manager', 'sync', {'context': {}})

        # Run the sync. engine at Coordo
        c.execute('sync.client.sync_manager', 'sync', {'context': {}})

    def runSyncCoordoProject(self):
        p = self.p
        c = self.c

        # Run the sync. engine at Coordo
        c.execute('sync.client.sync_manager', 'sync', {'context': {}})

        # Run the sync. engine at Project
        p.execute('sync.client.sync_manager', 'sync', {'context': {}})

    def sourceOSTLines(self, ost_ids):
        c = self.c
        p = self.p

        po_cft = 'dpo'
        fo_name = False
        for ost_id in ost_ids:
            ost = c.sourcing_line.browse(ost_id)

            supplier_ids = c.partner.search([('name', '=', 'ITCompany')])
            self.assert_(supplier_ids, 'No supplier ITCompany found in COORDO_01 !')
            fo_name = ost.sale_order_id.name
            values = {'supplier': supplier_ids[0],
                      'type': 'make_to_order',
                      'po_cft': po_cft,}
            po_cft = 'po'
            c.sourcing_line.write([ost_id], values)
            c.execute('sourcing.line', 'confirmLine', [ost_id])

        return ost, fo_name

    def validatePOs(self, po_ids):
        c = self.c
        # Validate the PO
        c.purchase.write(po_ids, {'delivery_confirmed_date': time.strftime('%Y-%m-%d')})
        for po_id in po_ids:
            c.exec_workflow('purchase.order', 'purchase_confirm', po_id)
        # Confirm the PO
        c.execute('purchase.order', 'confirm_button', po_ids)

        self.runSyncCoordoProject()

    def runTest(self):
        p = self.p
        c = self.c

        ad_id = self.getAnalyticDistribution()

        # Looking for the COORDO_01 partner
        partner_name = '%sCOORDO_01' % DB_SUFFIX
        partner, addr_ids = self.getPartners(partner_name)

        # Get the pricelist of the partner COORDO_01
        pricelist_id = partner.property_product_pricelist_purchase.id

        # Search the stock location Input
        location_ids = p.location.search([('name', '=', 'Input')])
        self.assert_(location_ids, 'No location Input found in PROJECT_01 !')

        # Create PO
        p_po_id = p.purchase.create({'partner_id': partner.id,
                                     'partner_address_id': addr_ids[0],
                                     'location_id': location_ids[0],
                                     'analytic_distribution_id': ad_id,
                                     'pricelist_id': pricelist_id})
        p_po_name = p.purchase.read(p_po_id, ['name'])['name']

        product_code = 'ADAPCABL1S-'
        product_ids = p.product.search([('default_code', '=', product_code)])
        self.assert_(product_ids, 'No product %s found !' % product_code)

        product = p.product.browse(product_ids[0])

        line_vals = {'product_id': product.id,
                     'product_qty': 50.00,
                     'price_unit': 0.00,
                     'product_uom': product.uom_id.id,
                     'name': product.name,
                     'order_id': p_po_id}

        p.po_line.create(line_vals)

        line_vals = {'product_id': product.id,
                     'product_qty': 25.00,
                     'price_unit': 0.00,
                     'product_uom': product.uom_id.id,
                     'name': product.name,
                     'order_id': p_po_id}

        p.po_line.create(line_vals)

        p.exec_workflow('purchase.order', 'purchase_confirm', p_po_id)

        self.runSyncProjectCoordo()

        # Get the FO created
        partner_ids = c.partner.search([('name', '=', '%sPROJECT_01' % DB_SUFFIX)])
        self.assert_(partner_ids, 'No partner PROJECT_01 found in COORDO_01 !')

        fo_ids = c.search('sale.order', [('partner_id', '=', partner_ids[0])], order='id desc')
        self.assert_(fo_ids, 'No FO created at Coordo for the partner PROJECT_01')

        # Validate the new FO
        c.exec_workflow('sale.order', 'order_validated', fo_ids[0])

        # Select DPO on OST and confirm the line
        ost = False
        ost_ids = c.sourcing_line.search([('sale_order_id', '=', fo_ids[0])])
        self.assert_(ost_ids, 'No OST line found for the FO − It seems that the FO hasn\'t been validated !')
        ost, fo_name = self.sourceOSTLines(ost_ids)
        
        fo_state =  c.sale.read(ost.sale_order_id.id, ['state'])['state']
        while fo_state != 'done':
            fo_state =  c.sale.read(ost.sale_order_id.id, ['state'])['state']
        
        fo_split_ids = c.sale.search([('name', '=', '%s-3' % fo_name)])
        self.assert_(fo_split_ids, 'No FO split found − May the FO was not split well !')
        
        # Run the scheduler
        proc_id = c.poca.create({})
        c.execute('procurement.order.compute.all', 'procure_calculation', [proc_id])
        
        po_ids = False
        while not po_ids:
            time.sleep(2)
            po_ids = c.purchase.search([('origin', 'like', '%s-3' % fo_name)])

        self.assert_(po_ids, 'No PO found with origin = \'%s-3\' in COORDO_01' % fo_name)
        not_dpo_ids = [x['id'] for x in c.purchase.read(po_ids, ['order_type']) if x['order_type'] != 'direct']


        self.validatePOs(po_ids)

        if not_dpo_ids:
            # Get the IN at COORDO and do the reception
            c_in_ids = c.picking.search([('purchase_id', 'in', not_dpo_ids)])
            self.assert_(c_in_ids, 'No IN found at COORDO')
            for c_in_id in c_in_ids:
                c_wiz_in = c.picking.action_process([c_in_id]).get('res_id', False)
                self.assert_(c_wiz_in, 'No wizard found to process IN at COORDO.')

                # Copy all
                try:
                    c.partial_pick.copy_all([c_wiz_in], {'model': 'stock.partial.picking'})
                    c.execute('stock.partial.picking', 'do_incoming_shipment', c_wiz_in)
                except error.RPCError as e:
                    print e
                    self.assert_(False, str(e))

            # Get the OUT at COORDO, convert it to standard OUT and process it
            c_out_ids = c.picking.search([('sale_id', 'in', fo_split_ids)])
            self.assert_(c_out_ids, 'No OUT found at COORDO')

            for c_out_id in c_out_ids:
                # Convert to standard
                c.picking.convert_to_standard([c_out_id])
                # Process it
                c_wiz_out = c.picking.action_process([c_out_id]).get('res_id', False)
                self.assert_(c_wiz_out, 'No wizard found to process OUT at COORDO')

                # Copy all
                try:
                    c.partial_pick.copy_all([c_wiz_out], {'model': 'stock.partial.picking'})
                    c.execute('stock.partial.picking', 'do_partial', c_wiz_out)
                except error.RPCError as e:
                    print e
                    self.assert_(False, str(e))


        self.runSyncCoordoProject()

        p_po_ids = p.purchase.search([('name', '=', '%s-3' % p_po_name)])
        # Get the IN
        p_in_ids = p.picking.search([('purchase_id', 'in', p_po_ids)])
        self.assert_(p_in_ids, 'No IN found in PROJECT')

        self.assertEqual(len(p_in_ids), 2, 'The number of IN at PROJECT is not equal to 2 : Result : %s' % len(p_in_ids))

        for p_in_id in p_in_ids:
            # Copy all and process the IN
            wiz_in_id = p.picking.action_process(p_in_id).get('res_id', False)
            self.assert_(wiz_in_id, 'No wizard found to process IN at PROJECT.')

            # Copy all
            try:
                p.partial_pick.copy_all([wiz_in_id], {'model': 'stock.partial.picking'})
                p.execute('stock.partial.picking', 'do_incoming_shipment', [wiz_in_id])
            except error.RPCError as e:
                print e
                self.assert_(False, str(e))

'''class DPOSyncTestCase2(DPOSyncTestCase):

    def sourceOSTLines(self, ost_ids):
        c = self.c
        p = self.p

        po_cft = 'dpo'
        fo_name = False
        supplier_ids = c.partner.search([('name', 'in', ('ITCompany', 'Afri Farmacia'))])
        supplier = supplier_ids[0]
        for ost_id in ost_ids:
            ost = c.sourcing_line.browse(ost_id)
            self.assert_(supplier_ids, 'No supplier ITCompany found in COORDO_01 !')
            fo_name = ost.sale_order_id.name
            values = {'supplier': supplier,
                      'type': 'make_to_order',
                      'po_cft': po_cft,}
            supplier = supplier_ids[1]
            c.sourcing_line.write([ost_id], values)
            c.execute('sourcing.line', 'confirmLine', [ost_id])

        return ost, fo_name

    def validatePOs(self, po_ids):
        c = self.c
        # Validate the PO
        c.purchase.write(po_ids, {'delivery_confirmed_date': time.strftime('%Y-%m-%d')})
        for po_id in po_ids:
            c.exec_workflow('purchase.order', 'purchase_confirm', po_id)
            # Confirm the PO
            c.execute('purchase.order', 'confirm_button', [po_id])

            self.runSyncCoordoProject()
'''

if __name__ == '__main__':
    unittest.main()
