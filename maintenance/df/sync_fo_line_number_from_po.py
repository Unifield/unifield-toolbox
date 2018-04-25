from oerplib import OERP

server_ip = '127.0.0.1'
xmlrcp_port = '8070'
#po_db = "SO_SOMA_OCA-20180423-013155-A-UF8.0"
#fo_db = "LN_KNYA_OCA-20180423-062200-A-UF8.0"
#po_name = '18/NL/SO001/PO00333'

po_db = "OCG_SS1_AGO-20180420-170831-UF8.0"
fo_db="OCG_SS1_COO-20180420-171207-UF8.0"
po_name="18/CH/SS160/PO00182"

user = 'admin'
password = 'admin'

oerp = OERP(server=server_ip, protocol='netrpc', port=xmlrcp_port, timeout=3600, version='6.0')
l = oerp.login(user, password, po_db)

pol = oerp.get('purchase.order.line')
ids = pol.search([('order_id.name', '=', po_name)])

d = {}
for line in pol.read(ids, ['line_number']):
    d[line['id']] = line['line_number']

l2 = oerp.login(user, password, fo_db)
sol = oerp.get('sale.order.line')
move = oerp.get('stock.move')

ids = sol.search([('order_id.client_order_ref', 'like', '%%%s'%po_name)])
for line in sol.read(ids, ['sync_linked_pol', 'line_number']):
    if not line['sync_linked_pol']:
        continue
    if not line['sync_linked_pol'].startswith(po_name):
        print line
        raise

    po_line = int(line['sync_linked_pol'].split('/')[-1])
    if d[po_line] != line['line_number']:
        print "update sale_order_line set line_number=%s where id=%s and line_number=%s;" % (d[po_line], line['id'], line['line_number'])
        mids = move.search([('sale_line_id', '=', line['id'])])
        #print move.read(mids, ['line_number'])
        if mids:
            print "update stock_move set line_number=%s where line_number=%s and id in (%s);" % (d[po_line], line['line_number'], ','.join(map(str,mids)))
