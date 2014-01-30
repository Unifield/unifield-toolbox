import oerplib

# Connect database on sync. engine
def connect_to_sync(conn):
    sync_client = conn.get('sync.client.sync_server_connection')
    sync_client.action_connect([1])


# Project
p = oerplib.OERP('localhost', protocol='xmlrpc', port=8069)
p_user = p.login('admin', 'admin', 'uf_2301_PROJECT_01')

# Coordo
c = oerplib.OERP('localhost', protocol='xmlrpc', port=8069)
c_user = c.login('admin', 'admin', 'uf_2301_COORDO_01')

print('Launch the connection to the sync. engine')
connect_to_sync(p)
connect_to_sync(c)

# At project, create a PO with one item

# Analytic distribution
print('Create analytic distribution')
analytic_id = p.search('account.analytic.account', [('code', '=', 'OPS')])
if not analytic_id:
    raise 'No Analytic account \'OPS\' found in database \'%s\'' % p.database
else:
    analytic_id = analytic_id[0]

destination_id = p.search('account.analytic.account', [('code', '=', 'HT101')])
if not destination_id:
    raise 'No Analytic account \'HT101\' found in database \'%s\'' % p.database
else:
    destination_id = destination_id[0]

ad = p.create('analytic.distribution', {'name': 'TEST QT uf_23301'})
ad_line = p.create('cost.center.distribution.line', {'name': 'CC Line 1',
                                                     'amount': 0.0,
                                                     'percentage': 100.00,
                                                     'currency_id': 1,
                                                     'analytic_id': analytic_id,
                                                     'distribution_id': ad,
                                                     'destination_id': destination_id})

# Partner
partner_name = 'uf_2301_COORDO_01'
partner = False
partner_id = p.search('res.partner', [('name', '=', partner_name)])
if not partner_id:
    raise 'No partner \'%s\' found in database \'%s\'' % (partner_name, p.database)
else:
    partner_id = partner_id[0]
    partner = p.browse('res.partner', partner_id)

# Address
addr_id = p.search('res.partner.address', [('partner_id', '=', partner_id)])
if not addr_id:
    raise 'No address found for the partner \'%s\' in the database \'%s\'' % (partner_name, p.database)
else:
    addr_id = addr_id[0]

# Pricelist
pricelist_id = partner.property_product_pricelist_purchase.id

# Location
location_id = p.search('stock.location', [('name', '=', 'Input')])
if not location_id:
    raise 'No location \'Input\' found in the database \'%s\'' % p.database
else:
    location_id = location_id[0]

print('Create PO')
po_id = p.create('purchase.order', {'partner_id': partner_id,
                                    'partner_address_id': addr_id,
                                    'location_id': location_id,
                                    'analytic_distribution_id': ad,
                                    'pricelist_id': pricelist_id})

# Add a line on this PO
print('Add line on PO')
product_code = 'ADAPCABL1S-'
product = False
product_id = p.search('product.product', [('default_code', '=', product_code)])
if not product_id:
    raise 'No product \'%s\' found in database \'%s\'' % (product_code, p.database)
else:
    product_id = product_id[0]
    product = p.browse('product.product', product_id)

line_vals = {'product_id': product_id,
             'product_qty': 50.00,
             'price_unit': 0.00,
             'product_uom': product.uom_id.id,
             'name': product.name,
             'order_id': po_id}

line_id = p.create('purchase.order.line', line_vals)

line_vals = {'product_id': product_id,
             'product_qty': 25.00,
             'price_unit': 0.00,
             'product_uom': product.uom_id.id,
             'name': product.name,
             'order_id': po_id}

line_id = p.create('purchase.order.line', line_vals)

# Validate the PO
print('Validate the PO')
p.exec_workflow('purchase.order', 'purchase_confirm', po_id)

# Run the sync. engine
print('Run the sync. engine')
sync_mgr = p.create('sync.client.sync_manager', {})
p.execute('sync.client.sync_manager', 'sync', {'context': {}})


#############
# At Coordo #
#############

# Run the sync. engine
print('Run the sync. engine at coordo')
sync_mgr = c.create('sync.client.sync_manager', {})
c.execute('sync.client.sync_manager', 'sync', {'context': {}})

# Get the FO created
partner_id = c.search('res.partner', [('name', '=', 'uf_2301_PROJECT_01')])
if not partner_id:
    raise 'No partner \'uf_2301_PROJECT_01\' found in database \'%s\'' % c.database
else:
    partner_id = partner_id[0]

fo_id = c.search('sale.order', [('partner_id', '=', partner_id)], order='id desc')
if not fo_id:
    raise 'No FO found in database \'%s\'' % c.database
else:
    fo_id = fo_id[0]

print('Validate the new FO')
c.exec_workflow('sale.order', 'order_validated', fo_id)

print('Select DPO on OST and confirm the line')
ost = False
ost_ids = c.search('sourcing.line', [('sale_order_id', '=', fo_id)])
if not ost_ids:
    raise 'No OST line found for FO in database \'%s\'' % c.database
else:
    for ost_id in ost_ids:
        ost = c.browse('sourcing.line', ost_id)

        supplier = c.search('res.partner', [('name', '=', 'ITCompany')])
        if not supplier:
            raise 'No supplier \'ITCompany\' found in database \'%s\'' % c.database
        else:
            supplier = supplier[0]

        fo_name = ost.sale_order_id.name
        values = {'supplier': supplier,
                  'type': 'make_to_order',
                  'po_cft': 'dpo',}
        c.write('sourcing.line', [ost_id], values)
        c.execute('sourcing.line', 'confirmLine', [ost_id])

fo_state =  c.read('sale.order', ost.sale_order_id.id, ['state'])['state']
while fo_state != 'done':
    fo_state =  c.read('sale.order', ost.sale_order_id.id, ['state'])['state']

fo_split_id = c.search('sale.order', [('name', '=', '%s-3' % fo_name)])
if not fo_split_id:
    raise 'No FO split found'
else:
    fo_split_id = fo_split_id[0]

print('Run the scheduler')
proc_id = c.create('procurement.order.compute.all', {})
c.execute('procurement.order.compute.all', 'procure_calculation', [proc_id])

po_id = False
while not po_id:
    po_id = c.search('purchase.order', [('origin', '=', '%s-3' % fo_name)])
if not po_id:
    raise 'No PO found with origin = \'%s\' in the database \'%s\'' % (fo_name, c.database)
else:
    po_id = po_id[0]

print('Validate the PO')
import time
c.write('purchase.order', [po_id], {'delivery_confirmed_date': time.strftime('%Y-%m-%d')})
c.exec_workflow('purchase.order', 'purchase_confirm', po_id)
print('Confirm the PO')
c.execute('purchase.order', 'confirm_button', [po_id])

# Run the sync. engine
print('Run the sync. engine at coordo')
sync_mgr = c.create('sync.client.sync_manager', {})
c.execute('sync.client.sync_manager', 'sync', {'context': {}})

# Run the sync. engine
print('Run the sync. engine at project')
sync_mgr = p.create('sync.client.sync_manager', {})
p.execute('sync.client.sync_manager', 'sync', {'context': {}})

