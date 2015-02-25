# -*- coding: utf-8 -*-

import random
import time

from chrono import TestChrono
from random_list import RandomList


class SupplyTestChrono(object):

    cases = {}

    def __init__(self, test_case):
        self.tc = test_case
        self.date = time.strftime('%Y-%m-%d %H:%M:%S')
        # Chronos
        self.valid_fo = TestChrono('fo_validation_time')
        self.confirm_fo = TestChrono('fo_confirmation_time')
        self.po_creation = TestChrono('po_creation_time')
        self.valid_po = TestChrono('po_validation_time')
        self.confirm_po = TestChrono('po_confirmation_time')
        self.process_in = TestChrono('in_processing_time')
        self.convert_out = TestChrono('out_convert_time')
        self.process_out = TestChrono('out_processing_time')
        self.process_pick = TestChrono('pick_processing_time')
        self.process_pack = TestChrono('pack_processing_time')
        self.process_ship = TestChrono('ship_processing_time')

        self.tc_number = 0
        if SupplyTestChrono.cases.get(self.tc.name, None):
            self.tc_number = len(SupplyTestChrono.cases[self.tc.name])

        SupplyTestChrono.cases.setdefault(self.tc.name, [])
        SupplyTestChrono.cases[self.tc.name].append(self)

        super(SupplyTestChrono, self).__init__()


class SupplyTestCase(object):

    def __init__(self, proxy, test_case):
        self.proxy = proxy
        self.tc = test_case
        # Get useful data for test case
        self.products = self.get_products()
        self.suppliers = self.get_suppliers()
        self.customers = self.get_customers()

        # Chronos
        self.chronos = SupplyTestChrono(self.tc)

        super(SupplyTestCase, self).__init__()

    def get_products(self):
        """
        Get a list of proudcts to use according to parameters (service
        products, batch mandatory products...)
        """
        if self.tc.with_tender:
            self.tc.nb_lines = self.tc.max_lines
        total_products = (self.tc.qty_per_month or 1) * self.tc.nb_lines

        nb_other_prd = total_products
        nb_srv_prd = nb_bm_prd = None
        if self.tc.service_products:
            nb_srv_prd = int((self.tc.service_products * total_products) / 100)
            nb_other_prd -= nb_srv_prd
        if self.tc.bm_products:
            nb_bm_prd = int((self.tc.bm_products * total_products) / 100)
            nb_other_prd -= nb_bm_prd

        products = RandomList()
        srv_prd_ids = self.proxy.prod.search([('type', '=', 'service_recep')])
        bm_prd_ids = self.proxy.prod.search([
            ('type', '=', 'product'),
            ('subtype', '=', 'single'),
            '|',
            ('batch_management', '=', True),
            ('perishable', '=', True),
        ])
        other_prd_ids = self.proxy.prod.search([
            ('type', '=', 'product'),
            ('batch_management', '=', False),
            ('perishable', '=', False),
            ('subtype', '=', 'single'),
        ])

        if nb_srv_prd and srv_prd_ids:
            products += [random.choice(srv_prd_ids) for x in range(nb_srv_prd)]
            total_products -= nb_srv_prd

        if nb_bm_prd and bm_prd_ids:
            products += [random.choice(bm_prd_ids) for x in range(nb_bm_prd)]
            total_products -= nb_bm_prd

        products += [random.choice(other_prd_ids) for x in range(total_products)]

        return products

    def get_suppliers(self):
        """
        Return the list of all external suppliers
        """
        p_ids = RandomList()
        partner_ids = self.proxy.partner.search([
            ('supplier', '=', True),
            ('partner_type', '=', 'external'),
        ])

        if not partner_ids:
            raise 'No supplier found in database !'

        nb_suppliers = self.tc.qty_per_month
        if self.tc.with_tender:
            nb_suppliers = self.tc.max_supplier

        return [random.choice(partner_ids) for x in range(nb_suppliers)]

    def get_customers(self):
        """
        """
        p_ids = RandomList()
        partner_ids = self.proxy.partner.search([
            ('customer', '=', True),
        ])

        if not partner_ids:
            raise 'No customer found in database !'

        return [random.choice(partner_ids) for x in range(self.tc.qty_per_month)]

    def get_in_received(self):
        """
        Return a list of booleans to know if the IN of the flow must be
        received or not according to percentage on each test case (received)
        """
        nb_received = self.tc.qty_per_month
        nb_bo = 0
        nb_two_bo = 0
        if self.tc.received:
            nb_received = int((self.tc.received * self.tc.qty_per_month) / 100)

        if self.tc.backordered:
            bo = int((self.tc.backordered * nb_received) / 100)

        if self.tc.two_backorders:
            nb_two_bo = int((self.tc.two_backorders * bo) / 100)

        in_bo = RandomList(False)
        in_bo += [True]*nb_bo
        in_bo += [False]*(nb_received-nb_bo)
        two_bo = RandomList(False)
        two_bo += [True]*nb_two_bo
        two_bo += [False]*(nb_bo-nb_two_bo)

        def get_rcv_tuple():
            bo = in_bo.pop()
            bo2 = bo and two_bo.pop() or False
            return (True, bo, bo2)

        self.in_received = RandomList((False, False, False))
        self.in_received += [get_rcv_tuple()]*nb_received
        self.in_received += [(False, False, False)]*(self.tc.qty_per_month-nb_received)

    def get_delivered(self):
        """
        Return a list on booleans to know if the Delivery Order of the flow
        has to be delivered according to percentage on each
        test case (delivered).
        """
        nb_delivered = self.tc.qty_per_month
        if self.tc.received:
            nb_delivered = int((self.tc.received * self.tc.qty_per_month) / 100)

        nb_received = nb_delivered

        if self.tc.delivered:
            nb_delivered = int((self.tc.delivered * nb_delivered) / 100)

        self.delivered = RandomList(False)
        self.delivered += [True]*nb_delivered
        self.delivered += [False]*(nb_received-nb_delivered)

    def get_pps(self):
        """
        Return a list on booleans to know if the Picking ticket of the flow
        has to be Picked, packed and shipped according to percentage on each
        test case (picked, packed, shipped).
        """
        nb_picked = self.tc.qty_per_month
        if self.tc.received:
            nb_picked = int((self.tc.received * self.tc.qty_per_month) / 100)

        if not nb_picked:
            nb_picked = 1

        nb_received = nb_picked
        if self.tc.picked:
            nb_picked = int((self.tc.picked * nb_picked) / 100)

        if not nb_picked:
            nb_picked = 1

        nb_packed = nb_picked
        if self.tc.packed:
            nb_packed = int((self.tc.packed * nb_packed) / 100)

        if not nb_packed:
            nb_packed = 1

        nb_shipped = nb_packed
        if self.tc.shipped:
            nb_shipped = int((self.tc.shipped * nb_shipped) / 100)

        if not nb_shipped:
            nb_shipped = 1

        packed = RandomList()
        packed += [True]*nb_packed
        packed += [False]*(nb_picked-nb_packed)
        shipped = RandomList()
        shipped += [True]*nb_shipped
        shipped += [False]*(nb_packed-nb_shipped)

        def _get_pps():
            pp = packed.pop()
            ps = pp and shipped.pop() or False
            return (True, pp, ps)

        self.pps = RandomList()
        self.pps += [_get_pps()]*nb_picked
        self.pps += [(False, False, False)]*(nb_received-nb_picked)

    def _get_cc(self, cc_name):
        """
        Get or create an analytic account
        """
        try:
            cc_id = self.proxy.ana_acc.search([
                ('name', '=', cc_name),
            ])[0]
        except IndexError:
            acc_id = self.proxy.data.get_object_reference(
                'analytic_distribution',
                'analytic_account_project',
            )[1]
            cc_id = self.proxy.ana_acc.create({
                'name': cc_name,
                'code': cc_name,
                'type': 'normal',
                'category': 'OC',
                'parent_id': acc_id,
                'date_start': time.strftime('%Y-01-01'),
            })

        return cc_id

    def _get_ad_line(self, acc_type, name, rate, cur, ana, ad, dest, cc=None):
        """
        Create a cost center or a funding pool line
        :param: acc_type: Type of line ('cc' for Cost center lines and 'fp' for
                          Funding Pool lines)
        :param: name: Name of the line
        :param: rate: Percentage of the line
        :param: cur: ID of the currency of the line
        :param: ana: ID of the analytic account
        :param: ad: ID of the analytic distribution
        :param: dest: ID of the destination account
        :param: cc: ID of the cost center
        """
        assert acc_type in ('cc', 'fp')
        assert acc_type != 'fp' or cc is not None

        values = {
            'name': name,
            'amount': 0.00,
            'percentage': rate,
            'currency_id': cur,
            'analytic_id': ana,
            'distribution_id': ad,
            'destination_id': dest,
        }

        if acc_type == 'cc':
            proxy_obj = self.proxy.cc
        else:
            proxy_obj = self.proxy.fp
            values.update({
                'cost_center_id': cc,
            })

        return proxy_obj.create(values)

    def _get_distrib(self):
        """
        Create an analytic distribution
        """
        # Create analytic accounts
        cc1_id = self._get_cc('CC1')
        cc2_id = self._get_cc('CC2')

        # Create analytic distribution
        ad_id = self.proxy.ad.create({'name': 'DISTRIB 1'})

        dest_id = self.proxy.data.get_object_reference(
            'analytic_distribution',
            'analytic_account_destination_operation',
        )[1]
        pf_id = self.proxy.data.get_object_reference(
            'analytic_distribution',
            'analytic_account_msf_private_funds',
        )[1]
        cur_id = self.proxy.data.get_object_reference(
            'base',
            'EUR',
        )[1]

        ccl1_id = self._get_ad_line(
            acc_type='cc',
            name='CC Line 1',
            rate='75.0',
            cur=cur_id,
            ana=cc1_id,
            ad=ad_id,
            dest=dest_id,
        )
        ccl2_id = self._get_ad_line(
            acc_type='cc',
            name='CC Line 2',
            rate='25.0',
            cur=cur_id,
            ana=cc1_id,
            ad=ad_id,
            dest=dest_id,
        )
        fpl1_id = self._get_ad_line(
            acc_type='cc',
            name='FP Line 1',
            rate='75.0',
            cur=cur_id,
            ana=pf_id,
            ad=ad_id,
            dest=dest_id,
            cc=cc1_id,
        )
        fpl1_id = self._get_ad_line(
            acc_type='cc',
            name='FP Line 2',
            rate='25.0',
            cur=cur_id,
            ana=pf_id,
            ad=ad_id,
            dest=dest_id,
            cc=cc2_id,
        )

        return ad_id

    def create_inventory(self, fo_line_ids, month):
        """
        Create an inventory with creation of batch numbers if needed
        """
        nomen_obj = self.proxy.conn.get('product.nomenclature')
        if month is None:
            month = time.strftime('%Y-12')

        inv_id = self.proxy.inventory.create({
            'name': self.tc.name,
            'date': '%s-01' % month,
        })

        location_id = self.proxy.data.get_object_reference(
            'stock', 'stock_location_stock')[1]
        med_loc_id = self.proxy.data.get_object_reference(
            'msf_config_locations', 'stock_location_medical')[1]
        log_loc_id = self.proxy.data.get_object_reference(
            'stock_override', 'stock_location_logistic')[1]
        med_nomen_id = nomen_obj.search([('name', '=', 'MED')])[0]
        log_nomen_id = nomen_obj.search([('name', '=', 'LOG')])[0]
        log_rt_id = self.proxy.data.get_object_reference(
            'reason_types_moves', 'reason_type_loss')[1]

        for fol in self.proxy.sol.browse(fo_line_ids):
            expiry_date = False
            prod_lot_id = False
            loc_id = location_id
            if fol.product_id.nomen_manda_0.id == med_nomen_id:
                loc_id = med_loc_id
            elif fol.product_id.nomen_manda_0.id == log_nomen_id:
                loc_id = log_loc_id

            if fol.product_id.perishable:
                lot_ids = self.proxy.lot.search([
                    ('product_id', '=', fol.product_id.id),
                ])
                if lot_ids:
                    expiry_date = self.proxy.lot.read(lot_ids[0], ['life_date'])['life_date']
                    prod_lot_id = lot_ids[0]
                else:
                    expiry_date = '20%s-%s-%s' % (
                        random.randint(int(time.strftime('%y')), 99),
                        random.randint(1, 12),
                        random.randint(1, 28),
                    )
                    if fol.product_id.batch_management:
                        prod_lot_id = self.proxy.lot.create({
                            'product_id': fol.product_id.id,
                            'name': '%s_%s_%s_%s' % (
                                expiry_date,
                                fol.product_id.id,
                                'INI_INV',
                                random.randint(1, 1000),
                            ),
                            'life_date': expiry_date,
                        })



            values = {
                'location_id': loc_id,
                'expiry_date': expiry_date,
                'reason_type_id': log_rt_id,
                'prod_lot_id': prod_lot_id,
                'product_id': fol.product_id.id,
                'inventory_id': inv_id,
                'product_uom': fol.product_uom.id,
            }
            values.update(self.proxy.inventory_line.on_change_product_id_specific_rules(
                False,
                loc_id,
                fol.product_id.id,
                prod_lot_id,
                fol.product_uom.id,
                '%s-01' % month,).get('value', {}))
            inv_line_ids = self.proxy.inventory_line.search([
                ('product_id', '=', fol.product_id.id),
                ('location_id', '=', loc_id),
            ])
            line_qty = values['product_qty'] + fol.product_uom_qty
            for inv_line in self.proxy.inventory_line.read(inv_line_ids, ['product_qty']):
                line_qty += inv_line['product_qty']
            values['product_qty'] = line_qty
            values['expiry_date'] = expiry_date
            values['prod_lot_id'] = prod_lot_id
            self.proxy.inventory_line.create(values)

        self.proxy.inventory.action_confirm([inv_id])
        self.proxy.inventory.action_done([inv_id])

    def validate_po(self, po_id):
        """
        Validate the PO
        :param po_id: ID of the purchase order to validate
        """
        po_brw = self.proxy.po.browse(po_id)
        drd = po_brw.delivery_requested_date.strftime('%Y-%m-%d')
        self.proxy.po.write([po_id], {
            'delivery_confirmed_date': drd,
        })

        # Add an analytic distribution on PO lines that have no
        no_ana_line_ids = self.proxy.pol.search([
            ('order_id', '=', po_id),
            ('analytic_distribution_id', '=', False),
        ])
        distrib_id = self._get_distrib()
        self.proxy.pol.write(no_ana_line_ids, {
            'analytic_distribution_id': distrib_id,
        })

        self.chronos.valid_po.start()
        self.proxy.exec_workflow(
            'purchase.order',
            'purchase_confirm',
            po_id)
        self.chronos.valid_po.stop()

        return True

    def confirm_po(self, po_id):
        """
        Confirm the PO
        :param po_id: ID of the purchase order to validate
        """
        po_not_confirmed = self.proxy.po.search([
            ('id', '=', po_id),
            ('state', '!=', 'confirmed'),
        ])
        if po_not_confirmed:
            raise "The state of the generated PO is not 'confirmed'"

        self.chronos.confirm_po.start()
        self.proxy.po.confirm_button([po_id])
        self.chronos.confirm_po.stop()

        return True

    def received_in(self, po_id, backordered=False, two_bo=False):
        """
        Make the reception of the IN
        :param po_id: ID of the purchase order attached to the IR to receive
        """
        po_date = self.proxy.po.read(po_id, ['delivery_confirmed_date'])['delivery_confirmed_date']
        in_ids = self.proxy.pick.search([
            ('purchase_id', '=', po_id),
            ('state', '=', 'assigned'),
        ])

        if not in_ids:
            return True

        self.chronos.process_in.start()
        for incoming in in_ids:
            in_proc_id = self.proxy.pick.action_process([incoming])['res_id']
            in_move_ids = self.proxy.in_proc_move.search([
                ('wizard_id', '=', in_proc_id),
            ])
            for im_id in self.proxy.in_proc_move.browse(in_move_ids):
                qty = im_id.ordered_quantity
                if backordered:
                    qty = random.randint(1, im_id.ordered_quantity)

                exp_date = None
                batch_id = None
                life_date = '20%s-%s-%s' % (
                    random.randint(int(time.strftime('%y')), 99),
                    random.randint(1, 12),
                    random.randint(1, 28),
                )
                if im_id.lot_check:
                    batch_id = self.proxy.lot.create({
                        'product_id': im_id.product_id.id,
                        'name': '%s_%s_%s' % (
                            im_id.product_id.id,
                            incoming,
                            random.randint(1, 1000),
                        ),
                        'life_date': life_date,
                    })

                self.proxy.in_proc_move.write([im_id.id], {
                    'quantity': qty,
                    'prodlot_id': im_id.lot_check and batch_id or False,
                    'expiry_date': im_id.exp_check and life_date or False,
                })

            self.proxy.in_proc.do_incoming_shipment([in_proc_id])
            in_state = self.proxy.pick.read(incoming, ['state'])['state']
            in_name = self.proxy.pick.read(incoming, ['name'])['name']
            while in_state != 'done' and not backordered:
                time.sleep(1)
                in_state = self.proxy.pick.read(incoming, ['state'])['state']

            invoice_ids = self.proxy.inv.search([
                ('picking_id', '=', incoming),
            ])
            if invoice_ids:
                self.proxy.inv.write(invoice_ids, {
                    'date_invoice': po_date,
                })
                self.proxy.hook_invoice(invoice_ids[0])

        if backordered and two_bo:
            self.received_in(po_id, True, False)
        elif backordered:
            self.received_in(po_id, False, False)
        self.chronos.process_in.stop()

        return True

    def is_ir(self):
        """
        Return True if the model of the test case is Internal Request.
        """
        return self.tc.model == 'internal.request'

    def is_internal_ir(self):
        """
        Return True if the test case uses an Internal Request with
        an internal location.
        """
        return self.is_ir() and self.tc.ir_type == 'internal'

    # sale.order methods
    def source_lines(self, line_ids):
        supplier_id = random.choice(self.suppliers)
        self.proxy.sol.write(line_ids, {
            'supplier': supplier_id,
            'po_cft': 'po',
        })

    def update_incoming_shipment(self, po_id):
        in_ids = self.proxy.pick.search([
            ('purchase_id', '=', po_id),
        ])
        po_date = self.proxy.po.read(po_id, ['delivery_confirmed_date'])['delivery_confirmed_date']
        move_ids = self.proxy.move.search([
            ('picking_id', 'in', in_ids),
        ])
        self.proxy.move.write(move_ids, {
            'date': po_date,
            'date_expected': po_date,
        })
        self.proxy.pick.write(in_ids, {
            'date': po_date,
            'min_date': po_date,
            'manual_min_date_stock_picking': po_date,
        })


class POFromScratchTestCase(SupplyTestCase):

    def __init__(self, proxy, test_case):
        """
        Get some random data
        """
        super(POFromScratchTestCase, self).__init__(proxy, test_case)
        self.get_po_categ()
        self.get_po_priority()
        self.get_in_received()

    def get_po_categ(self):
        """
        Return a list of PO categories to use according to percentage of
        each category in the test case (med_po, log_po and other_po).
        """
        nb_med_po = 0
        nb_log_po = 0
        if self.tc.med_po:
            nb_med_po = int((self.med_po * self.tc.qty_per_month) / 100)
        if self.tc.log_po:
            nb_log_po = int((self.log_po * self.tc.qty_per_month) / 100)

        po_categ = RandomList('other')
        po_categ += ['med']*nb_med_po 
        po_categ += ['log']*nb_log_po
        po_categ += ['other']*(self.tc.qty_per_month-nb_med_po-nb_log_po)

        self.po_categories = po_categ

    def get_po_priority(self):
        """
        Return a list of PO priorities to use according to percentage of
        each priority in the test case (emergency_po, normal_po)
        """
        nb_em_po = 0
        if self.tc.emergency_po:
            nb_em_po = int((self.emergency_po * self.tc.qty_per_month) / 100)

        po_prio = RandomList('normal')
        po_prio += ['emergency']*nb_em_po
        po_prio += ['normal']*(self.tc.qty_per_month-nb_em_po)

        self.po_priorities = po_prio

    def create_po_from_scratch(self, month=None):
        """
        Create the PO from scratch
        """
        if month is None:
            month = time.strftime('%Y-%m')

        po_date = '%s-%s' % (month, random.randint(1, 28))
        partner_id = self.suppliers.pop()

        po_values = {
            'partner_id': partner_id,
            'order_type': 'regular',
            'categ': self.po_categories.pop(),
            'priority': self.po_priorities.pop(),
            'date_order': po_date,
            'notes': self.tc.name,
            'delivery_requested_date': po_date,
            'delivery_confirmed_date': po_date,
            'cross_docking_ok': False,
        }

        po_values.update(self.proxy.po.onchange_partner_id(
            [], partner_id, po_date).get('value', {}))

        return self.proxy.po.create(po_values)

    def create_po_line(self, po_id):
        """
        Create PO line
        :param po_id: ID of the Po on which the line must be added
        """
        po_brw = self.proxy.po.browse(po_id)
        product_id = self.products.pop()
        product_qty = random.randint(1, 1000)

        line_values = {
            'order_id': po_id,
            'product_id': product_id,
            'product_qty': product_qty,
        }
        line_values.update(self.proxy.pol.product_id_on_change(
            [],
            po_brw.pricelist_id.id,
            product_id,
            product_qty,
            False,
            po_brw.partner_id.id,
            po_brw.date_order.strftime('%Y-%m-%d'),
            po_brw.fiscal_position,
            po_brw.date_order.strftime('%Y-%m-%d'),
            '',
            0.00,
            po_brw.state,
            0.00,
            False,
            False,
            {},
        ).get('value', {}))

        return self.proxy.pol.create(line_values)

    def run(self, month=None):
        """
        Run the test case a number of times defined by the test case.
        :param month: Month on which documents must be created
        """
        for i in range(self.tc.qty_per_month):
            po_id = self.create_po_from_scratch(month)
            po_line_ids = []
            for j in range(self.tc.nb_lines):
                po_line_ids.append(self.create_po_line(po_id))

            self.validate_po(po_id)
            self.confirm_po(po_id)

            in_recept = self.in_received.pop()
            if in_recept[0]:
                self.received_in(po_id, in_recept[1], in_recept[2])

            self.update_incoming_shipment(po_id)


class FOTestCase(SupplyTestCase):

    def get_order_categories(self):
        """
        Return a list of FO categories to use according to percentage of
        each category in the test case (med_fo, log_fo and other_fo).
        """
        nb_med_fo = 0
        nb_log_fo = 0
        if self.tc.med_fo:
            nb_med_fo = int((self.tc.med_fo * self.tc.qty_per_month) / 100)
        if self.tc.log_fo:
            nb_log_fo = int((self.tc.log_fo * self.tc.qty_per_month) / 100)

        fo_categ = RandomList('other')
        fo_categ += ['medical']*nb_med_fo + ['log']*nb_log_fo
        fo_categ += ['other']*(self.tc.qty_per_month-nb_med_fo-nb_log_fo)

        return fo_categ

    def get_order_priorities(self):
        """
        Return a list of FO priorities to use according to percentage of
        each priority in the test case (emergency_fo, normal_fo)
        """
        nb_em_fo = 0
        if self.tc.emergency_fo:
            nb_em_fo = int((self.tc.emergency_fo * self.tc.qty_per_month) / 100)

        fo_prio = RandomList('normal')
        fo_prio += ['emergency']*nb_em_fo
        fo_prio += ['normal']*(self.tc.qty_per_month-nb_em_fo)

        return fo_prio

    def __init__(self, proxy, test_case):
        super(FOTestCase, self).__init__(proxy, test_case)
        self.o_cat = self.get_order_categories()
        self.o_prio = self.get_order_priorities()

    def get_pt_ids(self, fo_ids):
        """
        Return a list of Picking tickets to process
        """
        pt_ids = self.proxy.pick.search([
            ('sale_id', 'in', fo_ids),
            ('type', '=', 'out'),
            ('subtype', '=', 'picking'),
            ('state', 'in', ('draft', 'assigned')),
        ])
        return pt_ids

    def make_pps(self, fo_ids, pps, month):
        """
        Picked, packed and shipped the picking tickets associated to the test
        case according to values in pps parameter.
        """
        pt_ids = self.get_pt_ids(fo_ids)

        if not pt_ids or not pps or not pps[0]:
            return True
        for pt_id in pt_ids:
            ppl_id = None
            ship_id = None
            self.chronos.process_pick.start()
            pick_state = self.proxy.pick.read(pt_id, ['state', 'line_state'])
            if pick_state['state'] == 'draft' and pick_state['line_state'] != 'processed':
                not_av_move_ids = self.proxy.move.search([
                    ('picking_id', '=', pt_id),
                    ('state', '=', 'confirmed'),
                ])
                not_av_fo_line_ids = []
                for move in self.proxy.move.browse(not_av_move_ids):
                    if move.sale_line_id:
                        not_av_fo_line_ids.append(move.sale_line_id.id)
                self.create_inventory(not_av_fo_line_ids, month)
                self.proxy.pick.action_assign([pt_id])
                cpt_id = self.proxy.pick.create_picking([pt_id]).get('res_id')
                if self.proxy.pt_proc.browse(cpt_id).move_ids:
                    self.proxy.pt_proc.copy_all([cpt_id])
                    pt_id = self.proxy.pt_proc.do_create_picking([cpt_id]).get('res_id')

            pick_state = self.proxy.pick.read(pt_id, ['state'])['state']
            if pick_state == 'assigned':
                vpt_id = self.proxy.pick.validate_picking([pt_id]).get('res_id')
                self.proxy.vpt_proc.copy_all([vpt_id])
                ppl_id = self.proxy.vpt_proc.do_validate_picking([vpt_id]).get('res_id')

            self.chronos.process_pick.stop()
            if ppl_id and pps[1]:
                self.chronos.process_pack.start()
                ppl_proc_id = self.proxy.pick.ppl([ppl_id]).get('res_id')
                self.proxy.ppl_proc.do_ppl_step1([ppl_proc_id])
                ppl_family_ids = self.proxy.ppl_family.search([
                    ('wizard_id', '=', ppl_proc_id),
                ])
                self.proxy.ppl_family.write(ppl_family_ids, {'weight': 10})
                ship_id = self.proxy.ppl_proc.do_ppl_step2([ppl_proc_id]).get('res_id')
                self.chronos.process_pack.stop()
            if ship_id and pps[2]:
                self.chronos.process_ship.start()
                ship_proc_id = self.proxy.ship.create_shipment([ship_id]).get('res_id')
                ship2_id = self.proxy.ship_proc.do_create_shipment([ship_proc_id]).get('res_id')
                self.proxy.ship.validate([ship2_id])
                self.chronos.process_ship.stop()

        return True

    def get_fo_values(self, month=False):
        """
        Create a FO
        """
        if month is None:
            month = time.strftime('%Y-%m')

        partner_id = self.customers.pop()
        order_type = 'regular'
        order_date = '%s-%s' % (
            month,
            random.randint(1, 28),
        )

        values = self.proxy.so.onchange_partner_id(
            None,
            partner_id,
            order_type,
        ).get('value', {})

        # Add an analytic distribution
        ad_id = self._get_distrib()

        values.update({
            'order_type': order_type,
            'partner_id': partner_id,
            'date_order': order_date,
            'procurement_request': False,
            'ready_to_ship_date': order_date,
            'delivery_requested_date': order_date,
            'analytic_distribution_id': ad_id,
            'categ': self.o_cat.pop(),
            'priority': self.o_prio.pop(),
        })

        return values

    def get_fo_line_values(self, fo_id):
        """
        Create FO line
        :param fo_id: ID of the FO on which the line must be added
        """
        fo_brw = self.proxy.so.browse(fo_id)
        product_id = self.products.pop()
        product_qty = random.randint(1, 1000)
        prd_brw = self.proxy.prod.browse(product_id)

        line_values = {
            'order_id': fo_id,
            'product_id': product_id,
            'product_uom_qty': product_qty,
        }

        line_values.update(self.proxy.sol.product_id_change(
            False,
            fo_brw.pricelist_id.id,
            product_id,
            product_qty,
            prd_brw.uom_id.id,
            product_qty,
            prd_brw.uom_id.id,
            '',
            fo_brw.partner_id.id,
            'en_US',
            True,
            fo_brw.date_order.strftime('%Y-%m-%d'),
            False,
            fo_brw.fiscal_position,
            False,
        ).get('value', {}))

        return line_values

    def validate_fo(self, order_id):
        """
        Validate the given FO
        """
        self.chronos.valid_fo.start()
        self.proxy.exec_workflow(
                'sale.order',
                'order_validated',
                order_id,
            )
        self.chronos.valid_fo.stop()

    def confirm_fo(self, fo_id, line_ids):
        """
        Source and confirm sourcing of all FO lines
        """
        fo_date = self.proxy.so.read(fo_id, ['date_order'])['date_order']
        po_ids = set()
        po_lines = []

        self.source_lines(line_ids)
        self.chronos.confirm_fo.start()
        self.proxy.sol.confirmLine(line_ids)

        order_rd = self.proxy.so.read(fo_id, ['state', 'procurement_request'])
        order_state = order_rd['state']
        while order_state != 'done':
            time.sleep(0.5)
            order_state = self.proxy.so.read(fo_id, ['state'])['state']
        self.chronos.confirm_fo.stop()

        new_order_ids = self.proxy.so.search([
            ('original_so_id_sale_order', '=', fo_id)
        ])

        if not (len(new_order_ids) > 0):
            raise "No split of FO found !"

        if new_order_ids:
            fo_id = new_order_ids[0]
            line_ids = self.proxy.sol.search([
                ('order_id', '=', fo_id),
            ])

        self.proxy.proc.run_scheduler()
        not_sourced = True
        proc_ids = [x['procurement_id'][0] for x in \
                self.proxy.sol.read(line_ids, ['procurement_id']) \
                if x['procurement_id']]

        self.chronos.po_creation.start()
        if not self.tc.with_tender:
            stop = 0
            while not_sourced:
                not_sourced = self.proxy.proc.search([
                    ('id', 'in', proc_ids),
                    ('state', 'not in', ('ready', 'running')),
                ])
                time.sleep(1)
                stop += 1
                if stop >= 900:
                    fo_line_ids = self.proxy.sol.search([
                        ('procurement_id', 'in', not_sourced),
                    ])
                    self.create_inventory(fo_line_ids, month)
                    self.proxy.proc.run_scheduler()

        else:
            while not_sourced:
                not_sourced = self.proxy.proc.search([
                    ('id', 'in', proc_ids),
                    ('state', '!=', 'tender'),
                ])
        self.chronos.po_creation.stop()

        for line in self.proxy.sol.browse(line_ids):
            if line.procurement_id:
                po_lines.extend(self.proxy.pol.search([
                    ('procurement_id', '=', line.procurement_id.id),
                ]))

        for po_line in self.proxy.pol.read(po_lines, ['order_id']):
            po_ids.add(po_line['order_id'][0])

        self.proxy.po.write(list(po_ids), {
            'date_order': fo_date,
        })

        return new_order_ids, list(po_ids)


class IRTestCase(SupplyTestCase):

    def get_requestor_location(self):
        raise NotImplemented('Should be overrided by the sub-classes')

    def make_out(self, ir_ids):
        if isinstance(ir_ids, (int, long)):
            ir_ids = [ir_ids]

        out_ids = self.proxy.pick.search([
            ('sale_id', 'in', ir_ids),
            ('state', '=', 'assigned'),
            ('type', '=', 'out'),
            ('subtype', '=', 'standard'),
        ])
        if out_ids:
            self.chronos.process_out.start()
            for out_id in out_ids:
                out_proc_id = self.proxy.pick.action_process(out_id)['res_id']
                self.proxy.out_proc.copy_all(out_proc_id)
                self.proxy.out_proc.do_partial([out_proc_id])
            self.chronos.process_out.stop()


    def get_ir_values(self, month=False):
        """
        Create an IR
        """
        if month is None:
            month = time.strftime('%Y-%m')

        order_date = '%s-%s' % (
            month,
            random.randint(1, 28),
        )

        values = {
            'date_order': order_date,
            'procurement_request': True,
            'delivery_requested_date': order_date,
            'location_requestor_id': self.get_requestor_location(),
        }

        return values

    def get_ir_line_values(self, ir_id):
        """
        Create IR line
        :param ir_id: ID of the IR on which the line must be added
        """
        ir_brw = self.proxy.so.browse(ir_id)
        product_id = self.products.pop()
        product_qty = random.randint(1, 1000)
        prd_brw = self.proxy.prod.browse(product_id)

        line_values = {
            'order_id': ir_id,
            'product_id': product_id,
            'product_uom_qty': product_qty,
            'product_uom': prd_brw.uom_id.id,
        }

        line_values.update(self.proxy.sol.requested_product_id_change(
            False,
            product_id,
            '',
        ).get('value', {}))

        return line_values

    def validate_ir(self, order_id):
        """
        Validate the given IR
        """
        self.chronos.valid_fo.start()
        self.proxy.exec_workflow(
            'sale.order',
            'procurement_validate',
            order_id,
        )
        self.chronos.valid_fo.stop()

    def confirm_ir(self, ir_id, line_ids):
        """
        Source and confirm sourcing of all IR lines
        """
        po_ids = set()
        po_lines = []

        self.source_lines(line_ids)
        self.chronos.confirm_fo.start()
        self.proxy.sol.confirmLine(line_ids)

        order_rd = self.proxy.so.read(ir_id, ['state', 'procurement_request'])
        order_state = order_rd['state']
        while order_state not in ('progress', 'done'):
            time.sleep(0.5)
            order_state = self.proxy.so.read(ir_id, ['state'])['state']
        self.chronos.confirm_fo.stop()

        line_ids = self.proxy.sol.search([
            ('order_id', '=', ir_id),
        ])

        self.chronos.po_creation.start()
        self.proxy.proc.run_scheduler()
        not_sourced = True
        proc_ids = [x['procurement_id'][0] for x in \
                self.proxy.sol.read(line_ids, ['procurement_id']) \
                if x['procurement_id']]
        if not self.tc.with_tender:
            while not_sourced:
                not_sourced = self.proxy.proc.search([
                    ('id', 'in', proc_ids),
                    ('state', 'not in', ('ready', 'running')),
                ])
        else:
            while not_sourced:
                not_sourced = self.proxy.proc.search([
                    ('id', 'in', proc_ids),
                    ('state', '!=', 'tender'),
                ])
        self.chronos.po_creation.stop()

        for line in self.proxy.sol.browse(line_ids):
            if line.procurement_id:
                po_lines.extend(self.proxy.pol.search([
                    ('procurement_id', '=', line.procurement_id.id),
                ]))

        for po_line in self.proxy.pol.read(po_lines, ['order_id']):
            po_ids.add(po_line['order_id'][0])

        return ir_id, list(po_ids)


class TenderTestCase(SupplyTestCase):

    def source_lines(self, line_ids):
        self.proxy.sol.write(line_ids, {
            'po_cft': 'cft',
        })

    def get_tender(self, order_id):
        """
        Search the tender that sources the IR/FO
        """
        if isinstance(order_id, (int, long)):
            order_id = [order_id]

        tender_ids = set()

        order_line_ids = self.proxy.sol.search([('order_id', 'in', order_id)])
        proc_ids = [x['procurement_id'][0] for x in \
                self.proxy.sol.read(order_line_ids, ['procurement_id']) \
                if x['procurement_id']]

        for line in self.proxy.sol.browse(order_line_ids):
            if line.procurement_id and line.procurement_id.tender_id:
                tender_ids.add(line.procurement_id.tender_id.id)

        return list(tender_ids)

    def generate_rfq(self, tender_ids):
        """
        Select suppliers and generate RfQs
        """
        suppliers = set()
        self_sup = list(self.suppliers)
        nb_suppliers = random.randint(self.tc.min_supplier, self.tc.max_supplier)
        for i in range(nb_suppliers):
            suppliers.add(self_sup.pop())

        self.proxy.tender.write(tender_ids, {
            'supplier_ids': [(6, 0, list(suppliers))],
        })

        for tender_id in tender_ids:
            self.proxy.exec_workflow(
                'tender',
                'button_generate',
                tender_id)

    def validate_rfqs(self, tender_ids):
        """
        Set unit prices on RfQ lines and validate the RfQs
        """
        rfq_ids = self.proxy.po.search([
            ('tender_id', 'in', tender_ids),
            ('rfq_ok', '=', True),
        ])

        for rfq in self.proxy.po.browse(rfq_ids):
            for line in rfq.order_line:
                self.proxy.pol.write([line.id], {
                    'price_unit': random.random(),
                })
            self.proxy.po.write([rfq.id], {
                'valid_till': rfq.date_order.strftime('%Y-%m-%d'),
            })

        self.proxy.po.rfq_sent(rfq_ids)
        self.proxy.po.check_rfq_updated(rfq_ids)

    def update_source_tender(self, tender_ids):
        """
        Update the tender line by choosing one RfQ line per tender line
        Continue sourcing
        """
        for tender in self.proxy.tender.browse(tender_ids):
            for line in tender.tender_line_ids:
                rfq_lines = self.proxy.pol.search([
                    ('tender_line_id', '=', line.id),
                ])
                self.proxy.tender_line.write([line.id], {
                    'purchase_order_line_id': random.choice(rfq_lines),
                })

            self.proxy.exec_workflow(
                'tender',
                'button_done',
                tender.id,
            )

    def get_po_from_tender(self, tender_ids):
        """
        Return the list of PO IDs created by the tender
        """
        if isinstance(tender_ids, (int, long)):
            tender_ids = [tender_ids]

        return self.proxy.po.search([
            ('origin_tender_id', 'in', tender_ids),
        ])

class POFromFOTestCase(FOTestCase):

    def run(self, month=None):
        """
        Run the test case a number of times defined by the test case.
        :param month: Month on which documents must be created
        """
        self.get_in_received()
        self.get_pps()

        for i in range(self.tc.qty_per_month):
            fo_values = self.get_fo_values(month)
            fo_id = self.proxy.so.create(fo_values)
            fo_line_ids = []
            for j in range(self.tc.nb_lines):
                fo_line_values = self.get_fo_line_values(fo_id)
                fo_line_ids.append(
                    self.proxy.sol.create(fo_line_values)
                )

            self.validate_fo(fo_id)
            split_fo_ids, po_ids = self.confirm_fo(fo_id, fo_line_ids)
            for po_id in po_ids:
                self.validate_po(po_id)
                self.confirm_po(po_id)

                in_recept = self.in_received.pop()
                if in_recept[0]:
                    self.received_in(po_id, in_recept[1], in_recept[2])

                    tc_pps = self.pps.pop()
                    self.make_pps(split_fo_ids, tc_pps, month)

                self.update_incoming_shipment(po_id)


class POFromInternalIRTestCase(IRTestCase):

    def get_requestor_location(self):
        """
        Get or create external consumption unit
        """
        stock_id = self.proxy.data.get_object_reference(
            'stock', 'stock_location_stock')[1]
        test_ids = self.proxy.loc.search([
            ('name', '=', 'Test Location'),
            ('location_category', '=', 'stock'),
            ('usage', '=', 'internal'),
            ('location_id', '=', stock_id),
        ])
        if test_ids:
            return test_ids[0]

        test_id = self.proxy.loc.create({
            'name': 'Test Location',
            'location_category': 'stock',
            'usage': 'internal',
            'location_id': stock_id,
        })

        return test_id

    def run(self, month=None):
        """
        Run the test case a number of times defined by the test case.
        :param month: Month on which documents must be created
        """
        self.get_in_received()

        for i in range(self.tc.qty_per_month):
            ir_values = self.get_ir_values(month)
            ir_id = self.proxy.so.create(ir_values)
            ir_line_ids = []
            for j in range(self.tc.nb_lines):
                ir_line_values = self.get_ir_line_values(ir_id)
                ir_line_ids.append(
                    self.proxy.sol.create(ir_line_values)
                )

            self.validate_ir(ir_id)

            ir_id, po_ids = self.confirm_ir(ir_id, ir_line_ids)
            for po_id in po_ids:
                self.validate_po(po_id)
                self.confirm_po(po_id)

                in_recept = self.in_received.pop()
                if in_recept[0]:
                    self.received_in(po_id, in_recept[1], in_recept[2])

                self.update_incoming_shipment(po_id)


class POFromExternalIRTestCase(IRTestCase):

    def get_requestor_location(self):
        """
        Get or create external consumption unit
        """
        cust_id = self.proxy.data.get_object_reference(
            'stock', 'stock_location_customers')[1]
        ext_ids = self.proxy.loc.search([
            ('name', '=', 'External CU'),
            ('location_category', '=', 'consumption_unit'),
            ('usage', '=', 'customer'),
            ('location_id', '=', cust_id),
        ])
        if ext_ids:
            return ext_ids[0]

        ext_id = self.proxy.loc.create({
            'name': 'External CU',
            'location_category': 'consumption_unit',
            'usage': 'customer',
            'location_id': cust_id
        })

        return ext_id

    def run(self, month=None):
        """
        Run the test case a number of times defined by the test case.
        :param month: Month on which documents must be created
        """
        self.get_in_received()
        self.get_delivered()

        for i in range(self.tc.qty_per_month):
            ir_values = self.get_ir_values(month)
            ir_id = self.proxy.so.create(ir_values)
            ir_line_ids = []
            for j in range(self.tc.nb_lines):
                ir_line_values = self.get_ir_line_values(ir_id)
                ir_line_ids.append(
                    self.proxy.sol.create(ir_line_values)
                )

            self.validate_ir(ir_id)
            ir_id, po_ids = self.confirm_ir(ir_id, ir_line_ids)
            for po_id in po_ids:
                self.validate_po(po_id)
                self.confirm_po(po_id)

                in_recept = self.in_received.pop()
                if in_recept[0]:
                    self.received_in(po_id, in_recept[1], in_recept[2])
                    deliver = self.delivered.pop()
                    if deliver:
                        self.make_out(ir_id)

                self.update_incoming_shipment(po_id)


class POFromFOTenderTestCase(FOTestCase, TenderTestCase):

    def run(self, month=None):
        """
        Run the test case a number of times defined by the test case.
        :param month: Month on which documents must be created
        """
        self.get_in_received()
        self.get_pps()

        for i in range(self.tc.qty_per_month):
            fo_values = self.get_fo_values(month)
            fo_id = self.proxy.so.create(fo_values)
            fo_line_ids = []
            for j in range(random.randint(self.tc.min_lines, self.tc.max_lines)):
                fo_line_values = self.get_fo_line_values(fo_id)
                fo_line_ids.append(
                    self.proxy.sol.create(fo_line_values)
                )

            self.validate_fo(fo_id)
            new_fo_ids, po_ids = self.confirm_fo(fo_id, fo_line_ids)

            tender_ids = self.get_tender(new_fo_ids)
            self.generate_rfq(tender_ids)
            self.validate_rfqs(tender_ids)
            self.update_source_tender(tender_ids)

            po_ids = self.get_po_from_tender(tender_ids)

            in_recept = self.in_received.pop()
            for po_id in po_ids:
                self.validate_po(po_id)
                self.confirm_po(po_id)

                if in_recept[0]:
                    self.received_in(po_id, in_recept[1], in_recept[2])

                self.update_incoming_shipment(po_id)

            tc_pps = self.pps.pop()
            self.make_pps(new_fo_ids, tc_pps, month)


class POFromIRTenderTestCase(IRTestCase, TenderTestCase):

    def get_requestor_location(self):
        """
        Get or create external consumption unit
        """
        stock_id = self.proxy.data.get_object_reference(
            'stock', 'stock_location_stock')[1]
        test_ids = self.proxy.loc.search([
            ('name', '=', 'Test Location'),
            ('location_category', '=', 'stock'),
            ('usage', '=', 'internal'),
            ('location_id', '=', stock_id),
        ])
        if test_ids:
            return test_ids[0]

        test_id = self.proxy.loc.create({
            'name': 'Test Location',
            'location_category': 'stock',
            'usage': 'internal',
            'location_id': stock_id,
        })

        return test_id

    def run(self, month=None):
        """
        Run the test case a number of times defined by the test case.
        :param month: Month on which documents must be created
        """
        self.get_in_received()
        self.get_delivered()

        for i in range(self.tc.qty_per_month):
            ir_values = self.get_ir_values(month)
            ir_id = self.proxy.so.create(ir_values)
            ir_line_ids = []
            for j in range(random.randint(self.tc.min_lines, self.tc.max_lines)):
                ir_line_values = self.get_ir_line_values(ir_id)
                ir_line_ids.append(
                    self.proxy.sol.create(ir_line_values)
                )

            self.validate_ir(ir_id)
            ir_id, po_ids = self.confirm_ir(ir_id, ir_line_ids)

            tender_ids = self.get_tender(ir_id)
            self.generate_rfq(tender_ids)
            self.validate_rfqs(tender_ids)
            self.update_source_tender(tender_ids)
            po_ids = self.get_po_from_tender(tender_ids)

            in_recept = self.in_received.pop()
            for po_id in po_ids:
                self.validate_po(po_id)
                self.confirm_po(po_id)

                if in_recept[0]:
                    self.received_in(po_id, in_recept[1], in_recept[2])

                self.update_incoming_shipment(po_id)

            if self.tc.ir_type == 'external':
                 deliver = self.delivered.pop(random.randint(0, len(self.delivered)-1))
                 if deliver:
                     self.make_out(ir_id)


class FOFromStockTestCase(FOTestCase):

    def source_lines(self, line_ids):
        supplier_id = random.choice(self.suppliers)
        self.proxy.sol.write(line_ids, {
            'type': 'make_to_stock',
        })

    def run(self, month=None):
        """
        Run the test case a number of times defined by the test case.
        :param month: Month on which documents must be created
        """
        self.get_pps()

        for i in range(self.tc.qty_per_month):
            fo_values = self.get_fo_values(month)
            fo_id = self.proxy.so.create(fo_values)
            fo_line_ids = []
            for j in range(self.tc.nb_lines):
                fo_line_values = self.get_fo_line_values(fo_id)
                fo_line_ids.append(
                    self.proxy.sol.create(fo_line_values)
                )
            self.create_inventory(fo_line_ids, month)

            self.validate_fo(fo_id)
            split_fo_ids, po_ids = self.confirm_fo(fo_id, fo_line_ids)

            tc_pps = self.pps.pop()
            self.make_pps(split_fo_ids, tc_pps, month)
            

class InternalIRFromStockTestCase(IRTestCase):

    def source_lines(self, line_ids):
        supplier_id = random.choice(self.suppliers)
        self.proxy.sol.write(line_ids, {
            'type': 'make_to_stock',
        })

    def get_requestor_location(self):
        """
        Get or create external consumption unit
        """
        stock_id = self.proxy.data.get_object_reference(
            'stock', 'stock_location_stock')[1]
        test_ids = self.proxy.loc.search([
            ('name', '=', 'Test Location'),
            ('location_category', '=', 'stock'),
            ('usage', '=', 'internal'),
            ('location_id', '=', stock_id),
        ])
        if test_ids:
            return test_ids[0]

        test_id = self.proxy.loc.create({
            'name': 'Test Location',
            'location_category': 'stock',
            'usage': 'internal',
            'location_id': stock_id,
        })

        return test_id

    def run(self, month=None):
        """
        Run the test case a number of times defined by the test case.
        :param month: Month on which documents must be created
        """
        self.get_delivered()

        for i in range(self.tc.qty_per_month):
            ir_values = self.get_ir_values(month)
            ir_id = self.proxy.so.create(ir_values)
            ir_line_ids = []
            for j in range(self.tc.nb_lines):
                ir_line_values = self.get_ir_line_values(ir_id)
                ir_line_ids.append(
                    self.proxy.sol.create(ir_line_values)
                )
            self.create_inventory(ir_line_ids, month)

            self.validate_ir(ir_id)
            ir_id, po_ids = self.confirm_ir(ir_id, ir_line_ids)

            deliver = self.delivered.pop()
            if deliver:
                self.make_out(ir_id)


class ExternalIRFromStockTestCase(IRTestCase):

    def source_lines(self, line_ids):
        supplier_id = random.choice(self.suppliers)
        self.proxy.sol.write(line_ids, {
            'type': 'make_to_stock',
        })

    def get_requestor_location(self):
        """
        Get or create external consumption unit
        """
        cust_id = self.proxy.data.get_object_reference(
            'stock', 'stock_location_customers')[1]
        ext_ids = self.proxy.loc.search([
            ('name', '=', 'External CU'),
            ('location_category', '=', 'consumption_unit'),
            ('usage', '=', 'customer'),
            ('location_id', '=', cust_id),
        ])
        if ext_ids:
            return ext_ids[0]

        ext_id = self.proxy.loc.create({
            'name': 'External CU',
            'location_category': 'consumption_unit',
            'usage': 'customer',
            'location_id': cust_id
        })

        return ext_id

    def run(self, month=None):
        """
        Run the test case a number of times defined by the test case.
        :param month: Month on which documents must be created
        """
        self.get_delivered()

        for i in range(self.tc.qty_per_month):
            ir_values = self.get_ir_values(month)
            ir_id = self.proxy.so.create(ir_values)
            ir_line_ids = []
            for j in range(self.tc.nb_lines):
                ir_line_values = self.get_ir_line_values(ir_id)
                ir_line_ids.append(
                    self.proxy.sol.create(ir_line_values)
                )
            self.create_inventory(ir_line_ids, month)

            self.validate_ir(ir_id)
            ir_id, po_ids = self.confirm_ir(ir_id, ir_line_ids)
            deliver = self.delivered.pop(random.randint(0, len(self.delivered)-1))
            if deliver:
                self.make_out(ir_id)


class FOFromStockOnOrderTestCase(FOTestCase):

    def source_lines(self, line_ids):
        nb_lines = len(line_ids)
        from_stock = int((self.tc.from_stock * nb_lines)/100)
        
        super(FOFromStockOnOrderTestCase, self).source_lines(line_ids)
        
        if from_stock:
            self.proxy.sol.write(line_ids[:from_stock], {
                'type': 'make_to_stock',
            })
            supplier_id = random.choice(self.suppliers)
            self.proxy.sol.write(line_ids[from_stock:], {
                'type': 'make_to_order',
                'po_cft': 'po',
                'supplier': supplier_id,
            })
            

    def run(self, month=None):
        """
        Run the test case a number of times defined by the test case.
        :param month: Month on which documents must be created
        """
        self.get_in_received()
        self.get_pps()

        for i in range(self.tc.qty_per_month):
            fo_values = self.get_fo_values(month)
            fo_id = self.proxy.so.create(fo_values)
            fo_line_ids = []
            for j in range(self.tc.nb_lines):
                fo_line_values = self.get_fo_line_values(fo_id)
                fo_line_ids.append(
                    self.proxy.sol.create(fo_line_values)
                )
            self.create_inventory(fo_line_ids, month)

            self.validate_fo(fo_id)
            split_fo_ids, po_ids = self.confirm_fo(fo_id, fo_line_ids)
            for po_id in po_ids:
                self.validate_po(po_id)
                self.confirm_po(po_id)

                in_recept = self.in_received.pop()
                if in_recept[0]:
                    self.received_in(po_id, in_recept[1], in_recept[2])

            tc_pps = self.pps.pop()
            self.make_pps(split_fo_ids, tc_pps, month)


class InitialInventoryTestCase(SupplyTestCase):
    
    def create_lines(self, inv_id):
        """
        Create an inventory lines
        """
        nomen_obj = self.proxy.conn.get('product.nomenclature')

        location_id = self.proxy.data.get_object_reference(
            'stock', 'stock_location_stock')[1]
        med_loc_id = self.proxy.data.get_object_reference(
            'msf_config_locations', 'stock_location_medical')[1]
        log_loc_id = self.proxy.data.get_object_reference(
            'stock_override', 'stock_location_logistic')[1]
        med_nomen_id = nomen_obj.search([('name', '=', 'MED')])[0]
        log_nomen_id = nomen_obj.search([('name', '=', 'LOG')])[0]
        log_rt_id = self.proxy.data.get_object_reference(
            'reason_types_moves', 'reason_type_loss')[1]

        x8bm = 3
        x6bm = int(self.tc.nb_lines * 0.10)

        for i in range(self.tc.nb_lines):
            product_id = self.products.pop()
            prd_brw = self.proxy.prod.browse(product_id)

            if prd_brw.nomen_manda_0.id == med_nomen_id:
                loc_id = med_loc_id
            elif prd_brw.nomen_manda_0.id == log_nomen_id:
                loc_id = log_loc_id

            def create_line():
                expiry_date = False
                prodlot_name = False
                if prd_brw.perishable:
                    expiry_date = '20%s-%s-%s' % (
                        random.randint(int(time.strftime('%y')), 99),
                        random.randint(1, 12),
                        random.randint(1, 28),
                    )
                    if prd_brw.batch_management:
                        prodlot_name = '%s_%s_%s_%s' % (
                            expiry_date,
                            prd_brw.id,
                            'INI_INV',
                            random.randint(1, 1000),
                        )

                values = {
                    'location_id': loc_id,
                    'expiry_date': expiry_date,
                    'reason_type_id': log_rt_id,
                    'prodlot_name': prodlot_name,
                    'product_id': prd_brw.id,
                    'inventory_id': inv_id,
                    'product_uom': prd_brw.uom_id.id,
                }
                values.update(self.proxy.ini_inv_line.product_change(
                    False,
                    prd_brw.id,
                    loc_id,
                    'product_id',
                    True,
                    prodlot_name).get('value', {}))

                values['product_qty'] = random.randrange(1, 3000)
                self.proxy.ini_inv_line.create(values)

            nb_cl = 1
            if prd_brw.perishable:
                nb_cl = 2
                if x8bm:
                    nb_cl = 8
                    x8bm -= 1
                elif x6bm:
                    nb_cl = 6
                    x6bm -= 1

            for i in range(nb_cl):
                create_line()

    def run(self, month=None):
        """
        Run the test case a number of times defined by the test case.
        :param month: Month on which documents must be created
        """
        for i in range(self.tc.qty_per_month or 1):
            inv_id = self.proxy.ini_inv.create({
                'name': 'Test initial inventory',
            })
            self.create_lines(inv_id)

            self.proxy.ini_inv.action_confirm([inv_id])
            self.proxy.ini_inv.action_done([inv_id])


class PhysicalInventoryTestCase(SupplyTestCase):
    
    def create_lines(self, inv_id):
        """
        Create an inventory lines
        """
        nomen_obj = self.proxy.conn.get('product.nomenclature')

        if self.tc.use_cu:
            cu_ids = self.proxy.loc.search([
                ('name', '=', 'Test CU'),
                ('location_category', '=', 'consumption_unit'),
                ('usage', '=', 'internal'),
            ])
            if cu_ids:
                cu_id = cu_ids[0]
            else:
                cu_id = self.proxy.loc.create({
                    'name': 'Test CU',
                    'location_category': 'consumption_unit',
                    'usage': 'internal',
                    'location_id': self.proxy.data.get_object_reference(
                        'msf_config_locations',
                        'stock_location_consumption_units_view')[1],
                })
        else:
            cu_id = False

        location_id = self.proxy.data.get_object_reference(
            'stock', 'stock_location_stock')[1]
        med_loc_id = self.proxy.data.get_object_reference(
            'msf_config_locations', 'stock_location_medical')[1]
        log_loc_id = self.proxy.data.get_object_reference(
            'stock_override', 'stock_location_logistic')[1]
        med_nomen_id = nomen_obj.search([('name', '=', 'MED')])[0]
        log_nomen_id = nomen_obj.search([('name', '=', 'LOG')])[0]
        log_rt_id = self.proxy.data.get_object_reference(
            'reason_types_moves', 'reason_type_loss')[1]

        x8bm = 3
        x6bm = int(self.tc.nb_lines * 0.10)
        change_qty = 0

        for i in range(self.tc.nb_lines):
            change_qty += 1
            product_id = self.products.pop()
            prd_brw = self.proxy.prod.browse(product_id)

            if self.tc.use_cu:
                loc_id = cu_id
            elif prd_brw.nomen_manda_0.id == med_nomen_id:
                loc_id = med_loc_id
            elif prd_brw.nomen_manda_0.id == log_nomen_id:
                loc_id = log_loc_id

            def create_line(change_qty):
                expiry_date = False
                prod_lot_id = False
                expiry_date = '20%s-%s-%s' % (
                    random.randint(int(time.strftime('%y')), 99),
                    random.randint(1, 12),
                    random.randint(1, 28),
                )
                if prd_brw.batch_management:
                    prod_lot_id = self.proxy.lot.create({
                        'product_id': prd_brw.id,
                        'name': '%s_%s_%s_%s' % (
                            expiry_date,
                            prd_brw.id,
                            'INI_INV',
                            random.randint(1, 1000),
                        ),
                        'life_date': expiry_date,
                    })

                values = {
                    'location_id': loc_id,
                    'expiry_date': expiry_date,
                    'reason_type_id': log_rt_id,
                    'prod_lot_id': prod_lot_id,
                    'product_id': prd_brw.id,
                    'inventory_id': inv_id,
                    'product_uom': prd_brw.uom_id.id,
                }
                values.update(self.proxy.inventory_line.on_change_product_id_specific_rules(
                    False,
                    loc_id,
                    prd_brw.id,
                    prod_lot_id,
                    prd_brw.uom_id.id,
                    '01-01-01',).get('value', {}))
                product_qty = values['product_qty']
                if change_qty == 3:
                    change_qty = 0
                    product_qty += random.randrange(1, 1000)
                values.update({
                    'product_qty': product_qty,
                    'prod_lot_id': prod_lot_id,
                    'expiry_date': expiry_date,
                })
                self.proxy.inventory_line.create(values)

            nb_cl = 1
            if prd_brw.perishable:
                nb_cl = 2
                if x8bm:
                    nb_cl = 8
                    x8bm -= 1
                elif x6bm:
                    nb_cl = 6
                    x6bm -= 1

            for i in range(nb_cl):
                create_line(change_qty)

    def run(self, month=None):
        """
        Run the test case a number of times defined by the test case.
        :param month: Month on which documents must be created
        """
        for i in range(self.tc.qty_per_month or 1):
            inv_id = self.proxy.inventory.create({
                'name': 'Test physical inventory',
            })
            self.create_lines(inv_id)

            self.proxy.inventory.action_confirm([inv_id])
            self.proxy.inventory.action_done([inv_id])


class ConsumptionReportTestCase(SupplyTestCase):

    def run(self, month=None):
        """
        Run the test case a number of times defined by the test case.
        :param month: Month on which documents must be created
        """
        nomen_obj = self.proxy.conn.get('product.nomenclature')
        cust_id = self.proxy.data.get_object_reference(
            'stock', 'stock_location_internal_customers')[1]
        med_loc_id = self.proxy.data.get_object_reference(
            'msf_config_locations', 'stock_location_medical')[1]
        log_loc_id = self.proxy.data.get_object_reference(
            'stock_override', 'stock_location_logistic')[1]
        med_nomen_id = nomen_obj.search([('name', '=', 'MED')])[0]
        log_nomen_id = nomen_obj.search([('name', '=', 'LOG')])[0]

        if month is None:
            month = int(time.strftime('%m'))-1

        for i in range(self.tc.qty_per_month or 5):
            med_rac_id = self.proxy.rac.create({
                'cons_location_id': med_loc_id,
                'activity_id': cust_id,
                'period_from': '%s-%s-01' % (time.strftime('%Y'), month[-2:]),
                'period_to': '%s-%s-05' % (time.strftime('%Y'), month[-2:]),
            })
            log_rac_id = self.proxy.rac.create({
                'cons_location_id': log_loc_id,
                'activity_id': cust_id,
                'period_from': '%s-%s-01' % (time.strftime('%Y'), month[-2:]),
                'period_to': '%s-%s-05' % (time.strftime('%Y'), month[-2:]),
            })

            log_product_ids = self.proxy.prod.search([
                ('nomen_manda_0', '=', log_nomen_id),
                ('type', '=', 'product'),
            ])
            med_product_ids = self.proxy.prod.search([
                ('nomen_manda_0', '=', med_nomen_id),
                ('type', '=', 'product'),
            ])

            for lp in self.proxy.prod.browse(log_product_ids[:25]):
                l_values = {
                    'product_id': lp.id,
                    'uom_id': lp.uom_id.id,
                    'rac_id': log_rac_id,
                }
                l_values.update(self.proxy.racl.product_onchange(
                    False,
                    lp.id,
                    log_loc_id,
                    lp.uom_id.id,
                    False,
                ).get('value', {}))
                l_values['consumed_qty'] = int(l_values.get('product_qty', 0) * 0.10)

                if l_values['consumed_qty'] >= 0:
                    self.proxy.racl.create(l_values)

            nb_med = 0
            for mp in self.proxy.prod.browse(med_product_ids):
                if nb_med > 25:
                    break

                lot_ids = self.proxy.lot.search([
                    ('product_id', '=', mp.id),
                ])
                if not lot_ids:
                    continue
                for lot in self.proxy.lot.browse(lot_ids):
                    l_values = {
                        'product_id': mp.id,
                        'uom_id': mp.uom_id.id,
                        'rac_id': med_rac_id,
                        'prodlot_id': lot.id,
                        'expiry_date': lot.life_date.strftime('%Y-%m-%d'),
                    }
                    l_values.update(self.proxy.racl.product_onchange(
                        False,
                        mp.id,
                        med_loc_id,
                        mp.uom_id.id,
                        lot.id,
                    ).get('value', {}))

                    if mp.perishable and not mp.batch_management:
                        l_values.update(self.proxy.racl.change_expiry(
                            False,
                            lot.life_date.strftime('%Y-%m-%d'),
                            mp.id,
                            med_loc_id,
                            mp.uom_id.id,
                            '',
                        ).get('value', {}))
                    else:
                        l_values.update(self.proxy.racl.change_prodlot(
                            False,
                            mp.id,
                            lot.id,
                            lot.life_date.strftime('%Y-%m-%d'),
                            med_loc_id,
                            mp.uom_id.id,
                            '',
                        ).get('value', {}))

                    l_values['consumed_qty'] = int(l_values.get('product_qty', 0) * 0.10)

                    if l_values['consumed_qty'] >= 0:
                        self.proxy.racl.create(l_values)
                nb_med += 1

            self.proxy.rac.process_moves([med_rac_id, log_rac_id])

#    def run_complete_flow(self):
#        self.create_order()
#        # FO validation
#        self.fo_validation_chrono.measure(self.valid_fo)
#        self.source_lines()
#        # FO confirmation
#        self.fo_confirmation_chrono.measure(self.confirm_fo)
#        self.get_new_generated_fo()
#        # PO creation
#        self.po_creation_chrono.measure(self.run_scheduler)
#        self.get_generated_po()
#        # PO validation
#        self.po_validation_chrono.measure(self.run_po_validation)
#        # PO confirmation
#        self.po_confirmation_chrono.measure(self.run_po_confirmation)
#        self.get_generated_in()
#        # IN processing
#        self.in_processing_chrono.measure(self.process_in)
#        self.get_generated_out()
#        # OUT conversion
#        self.out_convert_chrono.measure(self.out_convert_to_standard)
#        # OUT processing
#        self.out_processing_chrono.measure(self.out_processing)
