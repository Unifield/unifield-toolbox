from oerplib import OERP

server_ip = '127.0.0.1'
xmlrcp_port = '8070'
po_db = "SO_SOMA_OCA-20180423-013155-A-UF8.0_light_5"

po_name = '18/NL/SO001/PO00333'
ir_name = '18/IR00296'
user = 'admin'
password = 'admin'

oerp = OERP(server=server_ip, protocol='netrpc', port=xmlrcp_port, timeout=3600, version='6.0')
l = oerp.login(user, password, po_db)

ir_id = oerp.get('sale.order').search([('name', '=', ir_name), ('procurement_request', '=', 't')])[0]
po_id = oerp.get('purchase.order').search([('name', '=', po_name)])[0]

pol = oerp.get('purchase.order.line')
sol = oerp.get('sale.order.line')

done_in = {}

for line_obj, obj_id in [(pol, po_id), (sol, ir_id)]:
    ids = line_obj.search([('order_id', '=', obj_id), ('state', 'in', ['confirmed', 'done'])])
    qty = {}

    if line_obj._name == 'purchase.order.line':
        pick_type = 'in'
        pick_rel_field = 'purchase_id'
        move_line_rel_field = 'purchase_line_id'
        line_qty = 'product_qty'
        table = 'purchase_order_line'
    else:
        pick_type = 'out'
        pick_rel_field ='sale_id'
        move_line_rel_field = "sale_line_id"
        line_qty = 'product_uom_qty'
        table = 'sale_order_line'

    print '-- %s' % line_obj._name
    p_key = {}
    order_info = {'done': {}, 'confirmed': {}}
    for line in line_obj.read(ids, ['line_number', 'product_id', line_qty, 'state']):
        p_id = line['product_id'][0]
        line['remaining'] = line[line_qty]
        line['product_qty'] = line[line_qty]
        order_info[line['state']].setdefault(p_id, []).append(line)

    pick = oerp.get('stock.picking')
    mov = oerp.get('stock.move')

    # done picking
    pick_ids = pick.search([('type', '=', pick_type), (pick_rel_field, '=', obj_id), ('state', '=', 'done')])
    mv_ids = mov.search([('state', '!=', 'cancel'), ('picking_id', 'in', pick_ids)])
    for move in mov.read(mv_ids, ['picking_id', 'line_number', 'product_id', 'product_qty', move_line_rel_field]):
        p_id = move['product_id'][0]
        if table == 'purchase_order_line':
            done_in.setdefault(p_id, []).append(move)

        if p_id in order_info['done']:
            found = False
            for order_line in order_info['done'][p_id]:
                if order_line['remaining'] >= move['product_qty']:
                    order_line['remaining'] -= move['product_qty']
                    if move['line_number'] != order_line['line_number'] or move[move_line_rel_field][0] != order_line['id']:
                        print("update stock_move set line_number=%s, original_qty_partial=%s, "+move_line_rel_field+"=%s where id=%s and line_number=%s and "+move_line_rel_field+"=%s;") % (order_line['line_number'], order_line['product_qty'], order_line['id'], move['id'], move['line_number'], move[move_line_rel_field][0])
                    found = True
                    break
            if not found:
                print "This move is done, but missing qty on done po line ! (tip: check if we have qty on confirmed po line)"
                print move
                raise
        elif p_id in order_info['confirmed']:
            found = False
            for order_line in order_info['confirmed'][p_id]:
                if order_line['remaining'] >= move['product_qty']:
                    order_line['remaining'] -= move['product_qty']
                    if move['line_number'] != order_line['line_number'] or move[move_line_rel_field][0] != order_line['id']:
                        print("update stock_move set line_number=%s, "+move_line_rel_field+"=%s where id=%s and line_number=%s and "+move_line_rel_field+"=%s;") % (order_line['line_number'], order_line['id'], move['id'], move['line_number'], move[move_line_rel_field][0])
                    found = True
                    break
            if not found:
                print "This move is done, but missing qty confirmed po line !"
                print move
                raise
        else:
            print "This product_id is not found on any po line !"
            print move
            raise

    order_line_not_done = []
    for prod in order_info['done']:
        for order_line in order_info['done'][prod]:
            if order_line['remaining'] != 0:
                order_line_not_done.append(order_line['id'])
                order_info['confirmed'].setdefault(order_line['product_id'][0], []).append(order_line)
    if order_line_not_done:
        print("update "+table+" set state='confirmed' where id in (%s);") % (','.join(map(str, order_line_not_done)),)
        print("update wkf_instance set state='active' where res_type='"+line_obj._name+"' and res_id in (%s);") % (','.join(map(str,order_line_not_done)),)
        print "update wkf_workitem set act_id=(select id from wkf_activity where name='confirmed' and wkf_id = (select id from wkf where osv='"+line_obj._name+"')) where inst_id in (select id from wkf_instance where res_type='"+line_obj._name+"' and res_id in (%s));" % ((','.join(map(str, order_line_not_done))))

    order_line_done = []
    for prod in order_info['confirmed']:
        for order_line in order_info['confirmed'][prod]:
            if order_line['remaining'] == 0:
                order_line_done.append(order_line['id'])
    if order_line_done:
        print("update "+table+" set state='done' where id in (%s);") % (','.join(map(str, order_line_done)),)
        print("update wkf_workitem set act_id=(select id from wkf_activity where name='done' and wkf_id = (select id from wkf where osv='"+line_obj._name+"')) where inst_id in (select id from wkf_instance where res_type='"+line_obj._name+"' and res_id in (%s));") % ((','.join(map(str, order_line_done))))


    # confirmed picking
    to_del = []
    pick_ids = pick.search([('type', '=', pick_type), (pick_rel_field, '=', obj_id), ('state', 'not in', ['cancel', 'done'])])
    mv_ids = mov.search([('state', '!=', 'cancel'), ('picking_id', 'in', pick_ids)])
    for move in mov.read(mv_ids, ['line_number', 'product_id', 'product_qty', move_line_rel_field, 'state', 'picking_id']):
        p_id = move['product_id'][0]
        if p_id in order_info['confirmed']:
            found = False
            for order_line in order_info['confirmed'][p_id]:
                if order_line['remaining'] >= move['product_qty']:
                    order_line['remaining'] -= move['product_qty']
                    if move['line_number'] != order_line['line_number'] or move[move_line_rel_field][0] != order_line['id']:
                        print("update stock_move set line_number=%s, "+move_line_rel_field+"=%s where id=%s and line_number=%s and "+move_line_rel_field+"=%s;") % (order_line['line_number'], order_line['id'], move['id'], move['line_number'], move[move_line_rel_field][0])
                    found = True
                    break
            if not found:
                to_del.append(move)
        else:
            raise

        # compare OUT line state with IN state
        if table == 'sale_order_line' and move['state'] in ('assigned', 'confirmed'):
            if p_id not in done_in:
                state = 'confirmed'
            else:
                for x in done_in[p_id]:
                    state = 'confirmed'
                    if x['product_qty'] == move['product_qty']:
                        x['product_qty'] = 0
                        state = 'assigned'
                        break
            if move['state'] != state:
                print "update stock_move set state='%s' where state='%s' and id=%s;" % (state, move['state'], move['id'])

    for prod in order_info['confirmed']:
        for order_line in order_info['confirmed'][prod]:
            if order_line['remaining'] != 0:
                available_move = to_del.pop()
                print ("update stock_move set line_number=%s, "+move_line_rel_field+"=%s, product_qty=%s, product_uos_qty=%s, original_qty_partial=-1, product_id=%s where id=%s;") % (order_line['line_number'], order_line['id'], order_line['remaining'], order_line['remaining'], prod, available_move['id'])

                # compare OUT line state with IN state
                if table == 'sale_order_line' and move['state'] in ('assigned', 'confirmed'):
                    if prod not in done_in:
                        state = 'confirmed'
                    else:
                        for x in done_in[prod]:
                            state = 'confirmed'
                            if order_line['remaining'] == x['product_qty']:
                                x['product_qty'] = 0
                                state = 'assigned'
                                break
                    if available_move['state'] != state:
                        print "update stock_move set state='%s' where state='%s' and id=%s;" % (state, available_move['state'], available_move['id'])

    for d in to_del:
        print "update stock_move set "+move_line_rel_field+"=NULL, product_qty=0, product_uos_qty=0, state='cancel' where id=%s;" % (d['id'],)

print """
-- create view inc as (select product_id, sum(product_qty) from stock_picking p, stock_move m where m.picking_id=p.id and p.purchase_id=%(po_id)s and m.type='in'and m.state != 'cancel' group by product_id);
-- create view po as (select product_id, sum(product_qty) from purchase_order_line where order_id=%(po_id)s and state not in ('cancel', 'cancel_r') group by product_id);
-- create view out as (select m.product_id,sum(m.product_qty) from stock_move m, stock_picking p where m.picking_id = p.id and p.sale_id=%(ir_id)s and p.type='out' and m.state !='cancel' group by m.product_id order by m.product_id);
-- create view so as (select product_id, sum(product_uom_qty) from sale_order_line where state not in ('cancel', 'cancel_r') and order_id=%(ir_id)s group by product_id);
-- -- compare IR / OUT qty
-- select p.default_code, so.sum, out.sum from so left join out on so.product_id = out.product_id left join product_product p on p.id=so.product_id where so.sum!=coalesce(out.sum, 0);
-- select p.default_code, so.sum, out.sum from out left join so on so.product_id = out.product_id left join product_product p on p.id=out.product_id where out.sum!=coalesce(so.sum, 0);
-- -- compare IR / PO qty
-- select  p.default_code, so.sum, po.sum from so left join po on so.product_id = po.product_id left join product_product p on p.id=so.product_id where so.sum!=coalesce(po.sum, 0);
-- select  p.default_code, so.sum, po.sum from po left join so on so.product_id = po.product_id left join product_product p on p.id=po.product_id where po.sum!=coalesce(so.sum, 0);
-- -- compare IN / PO qty
-- select  p.default_code, inc.sum, po.sum from po left join inc on po.product_id = inc.product_id left join product_product p on p.id=po.product_id where po.sum!=coalesce(inc.sum, 0);
-- select  p.default_code, inc.sum, po.sum from inc left join po on po.product_id = inc.product_id left join product_product p on p.id=inc.product_id where inc.sum!=coalesce(po.sum, 0);
""" % {'po_id': po_id, 'ir_id': ir_id}


