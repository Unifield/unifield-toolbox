-- BEGIN
-- attach to main pick (not processed)
update stock_move set product_qty=product_uos_qty, picking_id=21001 where state='confirmed' and id in (select m.id from stock_picking p, stock_move m where m.picking_id = p.id and p.subtype='picking' and p.type='out' and p.name like 'PICK/00666-%' and m.backmove_id is null and pt_created='f' and m.state!='done');
-- processed
update stock_move set state='confirmed', picking_id=21001 where state='assigned' and id in (select m.id from stock_picking p, stock_move m where m.picking_id = p.id and p.subtype='picking' and p.type='out' and p.name like 'PICK/00666-%' and m.backmove_id is null and pt_created='f' and m.state!='done');


INSERT INTO stock_move(picking_id, create_uid, create_date, write_date, write_uid, product_uos_qty, address_id, product_uom, price_unit, date_expected, date, prodlot_id, move_dest_id, product_qty, product_uos, location_id, name, note, product_id, auto_validate, price_currency_id, partner_id, company_id, priority, state, location_dest_id, tracking_id, product_packaging, expired_date, type, purchase_line_id, sale_line_id, not_chained, reason_type_id, product_type, comment, already_confirmed, to_correct_ok, has_to_be_resourced, sync_dpo, processed_stock_move, text_error, dpo_id, dpo_line_id, partner_id2, hidden_perishable_mandatory, hidden_batch_management_mandatory, subtype, asset_id, composition_list_id, original_from_process_stock_move, kol_lot_manual, to_consume_id_stock_move, kit_creation_id_stock_move, to_pack, width, location_output_id, backmove_packing_id, height, not_shipped, weight, initial_location, from_pack, length, pack_type, invoice_line_id, pt_created, location_virtual_id, backmove_id, line_number, original_qty_partial, in_out_updated, change_reason, move_cross_docking_ok, direct_incoming, location_requestor_rw, origin, price_changed, date_cancel, pick_shipment_id, is_ext_cu, linked_incoming_move, pack_info_id)
                     SELECT 21001, create_uid, create_date, write_date, write_uid,               0, address_id, product_uom, price_unit, date_expected, date, prodlot_id, move_dest_id,           0, product_uos,           8, name, note, product_id, auto_validate, price_currency_id, partner_id, company_id, priority, 'assigned',                5, tracking_id, product_packaging, expired_date, type, purchase_line_id, sale_line_id, not_chained, reason_type_id, product_type, comment, already_confirmed, to_correct_ok, has_to_be_resourced, sync_dpo, processed_stock_move, text_error, dpo_id, dpo_line_id, partner_id2, hidden_perishable_mandatory, hidden_batch_management_mandatory, subtype, asset_id, composition_list_id, original_from_process_stock_move, kol_lot_manual, to_consume_id_stock_move, kit_creation_id_stock_move, to_pack, width, location_output_id, backmove_packing_id, height, not_shipped, weight, initial_location, from_pack, length, pack_type, invoice_line_id, pt_created, location_virtual_id, backmove_id, line_number, original_qty_partial, in_out_updated, change_reason, move_cross_docking_ok, direct_incoming, location_requestor_rw, origin, price_changed, date_cancel, pick_shipment_id, is_ext_cu, linked_incoming_move, pack_info_id from stock_move where state='done' and id in (select m.id from stock_picking p, stock_move m where m.picking_id = p.id and p.subtype='picking' and p.type='out' and p.name like 'PICK/00666-%' and m.backmove_id is null and pt_created='f' and (product_uos_qty!=0 or product_qty!=0));

-- subPick done must not have qty=0 (PICK/00666-06)
update stock_move set product_qty = product_uos_qty where picking_id=21159 and state='done' and pt_created='f' and product_qty=0 and product_uos_qty!=0;

INSERT INTO stock_move(picking_id, create_uid, create_date, write_date, write_uid, product_uos_qty, address_id, product_uom, price_unit, date_expected, date, prodlot_id, move_dest_id, product_qty, product_uos, location_id, name, note, product_id, auto_validate, price_currency_id, partner_id, company_id, priority, state, location_dest_id, tracking_id, product_packaging, expired_date, type, purchase_line_id, sale_line_id, not_chained, reason_type_id, product_type, comment, already_confirmed, to_correct_ok, has_to_be_resourced, sync_dpo, processed_stock_move, text_error, dpo_id, dpo_line_id, partner_id2, hidden_perishable_mandatory, hidden_batch_management_mandatory, subtype, asset_id, composition_list_id, original_from_process_stock_move, kol_lot_manual, to_consume_id_stock_move, kit_creation_id_stock_move, to_pack, width, location_output_id, backmove_packing_id, height, not_shipped, weight, initial_location, from_pack, length, pack_type, invoice_line_id, pt_created, location_virtual_id, backmove_id, line_number, original_qty_partial, in_out_updated, change_reason, move_cross_docking_ok, direct_incoming, location_requestor_rw, origin, price_changed, date_cancel, pick_shipment_id, is_ext_cu, linked_incoming_move, pack_info_id)
                     SELECT 21001, create_uid, create_date, write_date, write_uid,               0, address_id, product_uom, price_unit, date_expected, date, prodlot_id, move_dest_id,           0, product_uos,           8, name, note, product_id, auto_validate, price_currency_id, partner_id, company_id, priority, 'confirmed',                5, tracking_id, product_packaging, expired_date, type, purchase_line_id, sale_line_id, not_chained, reason_type_id, product_type, comment, already_confirmed, to_correct_ok, has_to_be_resourced, sync_dpo, processed_stock_move, text_error, dpo_id, dpo_line_id, partner_id2, hidden_perishable_mandatory, hidden_batch_management_mandatory, subtype, asset_id, composition_list_id, original_from_process_stock_move, kol_lot_manual, to_consume_id_stock_move, kit_creation_id_stock_move, to_pack, width, location_output_id, backmove_packing_id, height, not_shipped, weight, initial_location, from_pack, length, pack_type, invoice_line_id, pt_created, location_virtual_id, backmove_id, line_number, original_qty_partial, in_out_updated, change_reason, move_cross_docking_ok, direct_incoming, location_requestor_rw, origin, price_changed, date_cancel, pick_shipment_id, is_ext_cu, linked_incoming_move, pack_info_id from stock_move where state='done' and id in (select m.id from stock_picking p, stock_move m where m.picking_id = p.id and p.subtype='picking' and p.type='out' and p.name like 'PICK/00666-%' and m.backmove_id is null and pt_created='f' and product_uos_qty=0 and product_qty=0);

update stock_move m set product_uos_qty=(select l.product_uom_qty from sale_order_line l where l.id=m.sale_line_id),  product_qty=(select l.product_uom_qty from sale_order_line l where l.id=m.sale_line_id)  where m.product_uos_qty=0 and m.product_qty=0 and m.state='confirmed' and m.picking_id=21001;

update stock_move m set backmove_id=(select m1.id from stock_move m1, stock_picking p1 where m1.picking_id=p1.id and p1.name='PICK/00666' and m1.line_number=m.line_number and COALESCE(m1.prodlot_id,0)=COALESCE(m.prodlot_id,0)) where picking_id in (select id from stock_picking where name like 'PPL/00666%') and backmove_id is null and state!='done';

update sale_order_line set state='confirmed' where state='done' and id in (select sale_line_id from stock_move where picking_id=21001 and state in ('confirmed', 'assigned') and product_uos_qty!=0 and product_qty!=0 and line_number not in (53, 60, 84)) and order_id=1554;
update sale_order_line set state='confirmed' where state='done' and order_id=1554 and line_number=16;
update wkf_workitem set
 act_id=(select id from wkf_activity where name='confirmed' and wkf_id = (select id from wkf where osv='sale.order.line'))
  where inst_id in (select id from wkf_instance where res_type='sale.order.line' and res_id in (select id from sale_order_line where state='confirmed' and order_id=1554 ));
update wkf_instance set state='active' where res_type='sale.order.line' and res_id in (select id from sale_order_line where state='confirmed' and order_id=1554 );

-- already in a PPL
update stock_move m set state='assigned', product_qty=0 where m.picking_id=21001 and m.state='confirmed' and line_number=53;
update stock_move set product_qty=1060.000 where id=90772 and line_number=53;
update stock_move m set state='assigned', product_qty=0 where m.picking_id=21001 and m.state='confirmed' and line_number=60;
update stock_move set product_qty=1020.0 where id=90835 and line_number=60;

update stock_move m set state='assigned', product_qty=7 where m.picking_id=21001 and m.state='confirmed' and line_number=75;
update stock_move m set product_qty=850.0 where m.picking_id=21001 and m.state='confirmed' and line_number=82;

-- qty 1 IN cancel
update stock_move m set product_qty=1.0, state='cancel' where m.picking_id=21001 and m.state='confirmed' and line_number=84;

update stock_move m set product_qty=183300 where m.picking_id=21001 and m.state='confirmed' and line_number=85;
-- issue with FO631

update stock_move m set product_qty=5010 where m.picking_id=21001 and m.state='confirmed' and line_number=99;
update stock_move m set product_qty=90308.0 where m.picking_id=21001 and m.state='confirmed' and line_number=105;
update stock_move m set product_qty=157338.0 where m.picking_id=21001 and m.state='confirmed' and line_number=106;

INSERT INTO stock_move(picking_id, create_uid, create_date, write_date, write_uid, product_uos_qty, address_id, product_uom, price_unit, date_expected, date, prodlot_id, move_dest_id, product_qty, product_uos, location_id, name, note, product_id, auto_validate, price_currency_id, partner_id, company_id, priority, state, location_dest_id, tracking_id, product_packaging, expired_date, type, purchase_line_id, sale_line_id, not_chained, reason_type_id, product_type, comment, already_confirmed, to_correct_ok, has_to_be_resourced, sync_dpo, processed_stock_move, text_error, dpo_id, dpo_line_id, partner_id2, hidden_perishable_mandatory, hidden_batch_management_mandatory, subtype, asset_id, composition_list_id, original_from_process_stock_move, kol_lot_manual, to_consume_id_stock_move, kit_creation_id_stock_move, to_pack, width, location_output_id, backmove_packing_id, height, not_shipped, weight, initial_location, from_pack, length, pack_type, invoice_line_id, pt_created, location_virtual_id, backmove_id, line_number, original_qty_partial, in_out_updated, change_reason, move_cross_docking_ok, direct_incoming, location_requestor_rw, origin, price_changed, date_cancel, pick_shipment_id, is_ext_cu, linked_incoming_move, pack_info_id)
                     SELECT 21001, create_uid, create_date, write_date, write_uid,               0, address_id, product_uom, price_unit, date_expected, date, 4739, move_dest_id,           100700, product_uos,           8, name, note, product_id, auto_validate, price_currency_id, partner_id, company_id, priority, 'assigned',                5, tracking_id, product_packaging, expired_date, type, purchase_line_id, sale_line_id, not_chained, reason_type_id, product_type, comment, already_confirmed, to_correct_ok, has_to_be_resourced, sync_dpo, processed_stock_move, text_error, dpo_id, dpo_line_id, partner_id2, hidden_perishable_mandatory, hidden_batch_management_mandatory, subtype, asset_id, composition_list_id, original_from_process_stock_move, kol_lot_manual, to_consume_id_stock_move, kit_creation_id_stock_move, to_pack, width, location_output_id, backmove_packing_id, height, not_shipped, weight, initial_location, from_pack, length, pack_type, invoice_line_id, pt_created, location_virtual_id, backmove_id, line_number, original_qty_partial, in_out_updated, change_reason, move_cross_docking_ok, direct_incoming, location_requestor_rw, origin, price_changed, date_cancel, pick_shipment_id, is_ext_cu, linked_incoming_move, pack_info_id from stock_move where state='done' and line_number=16 and picking_id=21001;

INSERT INTO stock_move(picking_id, create_uid, create_date, write_date, write_uid, product_uos_qty, address_id, product_uom, price_unit, date_expected, date, prodlot_id, move_dest_id, product_qty, product_uos, location_id, name, note, product_id, auto_validate, price_currency_id, partner_id, company_id, priority, state, location_dest_id, tracking_id, product_packaging, expired_date, type, purchase_line_id, sale_line_id, not_chained, reason_type_id, product_type, comment, already_confirmed, to_correct_ok, has_to_be_resourced, sync_dpo, processed_stock_move, text_error, dpo_id, dpo_line_id, partner_id2, hidden_perishable_mandatory, hidden_batch_management_mandatory, subtype, asset_id, composition_list_id, original_from_process_stock_move, kol_lot_manual, to_consume_id_stock_move, kit_creation_id_stock_move, to_pack, width, location_output_id, backmove_packing_id, height, not_shipped, weight, initial_location, from_pack, length, pack_type, invoice_line_id, pt_created, location_virtual_id, backmove_id, line_number, original_qty_partial, in_out_updated, change_reason, move_cross_docking_ok, direct_incoming, location_requestor_rw, origin, price_changed, date_cancel, pick_shipment_id, is_ext_cu, linked_incoming_move, pack_info_id)
                     SELECT 21001, create_uid, create_date, write_date, write_uid,               0, address_id, product_uom, price_unit, date_expected, date,  4650, move_dest_id,           156400, product_uos,           8, name, note, product_id, auto_validate, price_currency_id, partner_id, company_id, priority, 'assigned',                5, tracking_id, product_packaging, expired_date, type, purchase_line_id, sale_line_id, not_chained, reason_type_id, product_type, comment, already_confirmed, to_correct_ok, has_to_be_resourced, sync_dpo, processed_stock_move, text_error, dpo_id, dpo_line_id, partner_id2, hidden_perishable_mandatory, hidden_batch_management_mandatory, subtype, asset_id, composition_list_id, original_from_process_stock_move, kol_lot_manual, to_consume_id_stock_move, kit_creation_id_stock_move, to_pack, width, location_output_id, backmove_packing_id, height, not_shipped, weight, initial_location, from_pack, length, pack_type, invoice_line_id, pt_created, location_virtual_id, backmove_id, line_number, original_qty_partial, in_out_updated, change_reason, move_cross_docking_ok, direct_incoming, location_requestor_rw, origin, price_changed, date_cancel, pick_shipment_id, is_ext_cu, linked_incoming_move, pack_info_id from stock_move where state='done' and line_number=16 and picking_id=21001;

update stock_move m set state='confirmed', product_qty=198200, prodlot_id=NULL where m.picking_id=21001 and m.state='done' and line_number=16;


update stock_move set product_qty=0 where id=90065 and line_number=114;
update stock_move set product_qty=0 where id=90063 and line_number=113;
update stock_move set product_qty=0 where id in (89113, 88879) and line_number=112;
update stock_move set product_qty=0 where id in (89541,89133, 89154) and line_number=51;
update stock_move set product_qty=0 where id in (89554,89132,89153) and line_number=50;
update stock_move set product_qty=0 where id in (88876,89110) and line_number=49;
update stock_move set product_qty=0 where id in (88875,89109)  and line_number=46;
update stock_move set product_qty=0 where id in (88874,89108) and line_number=45;
update stock_move set product_qty=0 where id in (88873, 89107) and line_number=44;
update stock_move set product_qty=0 where id in (88872, 89106) and line_number=43;
update stock_move set product_qty=0 where id in (88871,89105) and line_number=33;
update stock_move set product_qty=0 where id in (89079, 89103,89104,88868,88870,88869) and line_number=32;
update stock_move set product_qty=0 where id in (89102, 88867) and line_number=28;
update stock_move set product_qty=0 where id in (88866, 89101) and line_number=26;
update stock_move set product_qty=0 where id in (89100,88865) and line_number=25;
update stock_move set product_qty=0 where id in (89099,88864) and line_number=20;
update stock_move set product_qty=0 where id in (88863, 89098) and line_number=19;
update stock_move set product_qty=0 where id in (89096, 89097,88861,88862) and line_number=17;
update stock_move set product_qty=0 where id in (89095,88860) and line_number=8;
update stock_move set product_qty=0 where id in (89094,89093,88858,88859) and line_number=7;
update stock_move set product_qty=0 where id in (89092,88857) and line_number=2;
update stock_move set product_qty=0 where id in (89091,88856) and line_number=1;

update stock_picking set line_state='mixed' where id=21001;


update stock_picking set state='done' where id=21159;

-- debug
-- select m.id, m.product_qty,m.state,p.name from stock_move m, stock_picking p where m.picking_id=p.id and sale_line_id in (select id from sale_order_line where order_id=1554 and line_number=32) order by p.name;
-- select m.id, m.product_qty,m.state,p.name from stock_move m, stock_picking p where m.picking_id=p.id and m.purchase_line_id in (select id from purchase_order_line where sale_order_line_id in (select id from sale_order_line where order_id=1554 and line_number=32)) order by p.name;
-- select p.name,m.product_qty from stock_move m, stock_picking p where m.picking_id=p.id and m.location_id=8 and m.state='assigned' and product_id=3746;
-- select product_id,sum(qty) from (select product_id,sum(-m1.product_qty) as qty from stock_move m1 where m1.location_id=8 and m1.location_dest_id!=8 and m1.state in ('done','assigned') group by product_id union select product_id, sum(m2.product_qty) as qty from stock_move m2 where m2.location_id!=8 and m2.location_dest_id=8 and m2.state in ('done') group by product_id) x where product_id=3745 group by product_id;
-- line 62 [ELAECCHT212]  / 20058505 assigned by FO00642
-- line 113 DINJINSHR1VN IN/01717 + IN/01718 : 56 sur PICK/00670-11, , PICK/00586-04/PICK/00507-85

-- ROLLBACK;
-- COMMIT;
