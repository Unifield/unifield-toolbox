#-*- coding: utf-8 -*-
import oerplib
import unittest
import time

DB_SUFFIX = 'uf_2320_'
PARTNER_SUFFIX = 'uf_2320_'

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


class UF2320SyncTestCase(unittest.TestCase):

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

        # Looking for the COORDO_01 partner
        partner_name = '%sCOORDO_01' % PARTNER_SUFFIX
        partner_ids = p.partner.search([('name', '=', partner_name)])
        self.assert_(partner_ids, 'Partner COORDO_01 not found in PROJECT_01 !')
        partner = p.partner.browse(partner_ids[0])

        # Search address for the partner COORDO_01
        addr_ids = p.addr.search([('partner_id', '=', partner_ids[0])])
        self.assert_(addr_ids, 'No address found for the partner COORDO_01 !')

        # Get the pricelist of the partner COORDO_01
        pricelist_id = partner.property_product_pricelist_purchase.id

        # Search the stock location Input
        location_ids = p.location.search([('name', '=', 'Input')])
        self.assert_(location_ids, 'No location Input found in PROJECT_01 !')

        # Create PO
        po_id = p.purchase.create({'partner_id': partner_ids[0],
                                   'partner_address_id': addr_ids[0],
                                   'location_id': location_ids[0],
                                   'analytic_distribution_id': ad_id,
                                   'pricelist_id': pricelist_id})

        product_code = 'DINJCEFA1V-'
        product_ids = p.product.search([('default_code', '=', product_code)])
        self.assert_(product_ids, 'No product %s found !' % product_code)

        product = p.product.browse(product_ids[0])

        line_vals = {'product_id': product.id,
                     'product_qty': 50.00,
                     'price_unit': 0.00,
                     'product_uom': product.uom_id.id,
                     'name': product.name,
                     'order_id': po_id}

        p.po_line.create(line_vals)

        p.exec_workflow('purchase.order', 'purchase_confirm', po_id)

        # Run the sync. engine
        p.execute('sync.client.sync_manager', 'sync', {'context': {}})


        #############
        # At Coordo #
        #############

        # Run the sync. engine
        c.execute('sync.client.sync_manager', 'sync', {'context': {}})

        # Get the FO created
        partner_ids = c.partner.search([('name', '=', '%sPROJECT_01' % PARTNER_SUFFIX)])
        self.assert_(partner_ids, 'No partner PROJECT_01 found in COORDO_01 !')

        fo_ids = c.search('sale.order', [('partner_id', '=', partner_ids[0])], order='id desc')
        self.assert_(fo_ids, 'No FO created at Coordo for the partner PROJECT_01')

        # Validate the new FO
        c.exec_workflow('sale.order', 'order_validated', fo_ids[0])

        # Split the line then for each line,
        # Select PO on OST and confirm the line
        ost = False
        ost_ids = c.sourcing_line.search([('sale_order_id', '=', fo_ids[0])])
        self.assert_(ost_ids, 'No OST line found for the FO − It seems that the FO hasn\'t been validated !')
        for ost_id in ost_ids:
            ost = c.sourcing_line.browse(ost_id)
            wiz_id = c.sale_line.open_split_wizard([ost.sale_order_line_id.id]).get('res_id')
            self.assert_(wiz_id, 'No split line wizard opened')
            c.ssolw.write([wiz_id], {'new_line_qty': 15.0})

        ost_ids = c.sourcing_line.search([('sale_order_id', '=', fo_ids[0])])
        self.assert_(len(ost_ids) == 2, 'The OST line has not been split !')
        
        supplier_ids = c.partner.search([('name', 'in', ['ITCompany', 'Afri Farmacia'])])
        self.assert_(len(supplier_ids) == 2, 'No suppliers found in COORDO_01 !')
        i = 0
        for ost_id in ost_ids:
            fo_name = ost.sale_order_id.name
            values = {'supplier': supplier_ids[i],
                      'type': 'make_to_order',
                      'po_cft': 'po',}
            c.sourcing_line.write([ost_id], values)
            c.execute('sourcing.line', 'confirmLine', [ost_id])
            i += 1
        
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
            print fo_name
            po_ids = c.purchase.search([('origin', 'like', '%s-3' % fo_name)])

        self.assert_(po_ids, 'No PO found with origin = \'%s-3\' in COORDO_01' % fo_name)
        
        # Validate the PO
        c.purchase.write(po_ids, {'delivery_confirmed_date': time.strftime('%Y-%m-%d')})
        for po_id in po_ids:
            c.exec_workflow('purchase.order', 'purchase_confirm', po_id)
        # Confirm the PO
        c.execute('purchase.order', 'confirm_button', po_ids)
        
        # Run the sync. engine at coordo
        c.execute('sync.client.sync_manager', 'sync', {'context': {}})
        
        # Run the sync. engine at project
        p.execute('sync.client.sync_manager', 'sync', {'context': {}})
         

if __name__ == '__main__':
    unittest.main()
