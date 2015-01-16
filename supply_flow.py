# -*- coding: utf-8 -*-

import random
import time

from chrono import TestChrono


class SupplyFlow(object):

    def __init__(self, proxy):
        self.proxy = proxy
        self.min_lines = proxy.min_lines
        self.max_lines = proxy.max_lines
        self.fo_id = None
        self.fo_lines = []
        self.po_ids = None
        self.pol_lines = None
        self.in_ids = None
        self.out_ids = None
        self.fo_validation_chrono = TestChrono('fo_validation_time')
        self.fo_confirmation_chrono = TestChrono('fo_confirmation_time')
        self.po_creation_chrono = TestChrono('po_creation_time')
        self.po_validation_chrono = TestChrono('po_validation_time')
        self.po_confirmation_chrono = TestChrono('po_confirmation_time')
        self.in_processing_chrono = TestChrono('in_processing_time')
        self.out_convert_chrono = TestChrono('out_convert_time')
        self.out_processing_chrono = TestChrono('out_processing_time')

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
        self.ad_id = self.proxy.ad.create({'name': 'DISTRIB 1'})

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
            ad=self.ad_id,
            dest=dest_id,
        )
        ccl2_id = self._get_ad_line(
            acc_type='cc',
            name='CC Line 2',
            rate='25.0',
            cur=cur_id,
            ana=cc1_id,
            ad=self.ad_id,
            dest=dest_id,
        )
        fpl1_id = self._get_ad_line(
            acc_type='cc',
            name='FP Line 1',
            rate='75.0',
            cur=cur_id,
            ana=pf_id,
            ad=self.ad_id,
            dest=dest_id,
            cc=cc1_id,
        )
        fpl1_id = self._get_ad_line(
            acc_type='cc',
            name='FP Line 2',
            rate='25.0',
            cur=cur_id,
            ana=pf_id,
            ad=self.ad_id,
            dest=dest_id,
            cc=cc2_id,
        )

    def _get_fo_values(self):
        """
        Returns specific values for a Field order (partner, partner address,
        pricelist...)

        :return: The values of the order
        :rtype dict
        """
        partner_ids = self.proxy.partner.search([('customer', '=', True)])
        partner_id = random.choice(partner_ids)
        order_type = 'regular'

        values = self.proxy.so.onchange_partner_id(
            None,
            partner_id,
            order_type,
        ).get('value', {})

        # Add an analytic distribution
        self._get_distrib()

        values.update({
            'order_type': order_type,
            'procurement_request': False,
            'partner_id': partner_id,
            'ready_to_ship_date': time.strftime('%Y-%m-%d'),
            'analytic_distribution_id': self.ad_id,
        })

        return values

    def create_order(self):
        """
        Create a field order with a number of lines according to the
        configuration.
        """
        # Prepare values for the field order
        uom_pce_id = self.proxy.data.get_object_reference(
            'product', 'product_uom_unit')[1]

        self.fo_id = self.proxy.so.create(self._get_fo_values())

        # Create order lines
        line_values = {
            'order_id': self.fo_id,
            'product_uom': uom_pce_id,
            'type': 'make_to_order',
            'price_unit': random.randint(1, 250),
        }

        nb_lines = random.randint(self.min_lines, self.max_lines)
        for i in range(nb_lines):
            line_values.update({
                'product_id': random.choice(self.proxy.product_ids),
                'product_uom_qty': random.randint(1, 250),
            })
            self.fo_lines.append(self.proxy.sol.create(line_values))

        return self.fo_id

    def valid_fo(self):
        self.proxy.exec_workflow('sale.order', 'order_validated', self.fo_id)

    def confirm_fo(self):
        """
        Source and confirm sourcing of all FO lines
        """
        self.proxy.sol.confirmLine(self.fo_lines)

        order_state = self.proxy.so.read(self.fo_id, ['state'])['state']
        while order_state != 'done':
            time.sleep(0.5)
            order_state = self.proxy.so.read(self.fo_id, ['state'])['state']

    def get_new_generated_fo(self):
        new_order_ids = self.proxy.so.search([
            ('original_so_id_sale_order', '=', self.fo_id)
        ])

        if not (len(new_order_ids) > 0):
            raise "No split of FO found !"

        if new_order_ids:
            self.fo_id = new_order_ids[0]
            self.fo_lines = self.proxy.sol.search([
                ('order_id', '=', self.fo_id),
            ])

    def run_scheduler(self):
        self.proxy.proc.run_scheduler()
        not_sourced = True
        proc_ids = [x['procurement_id'][0] for x in \
                self.proxy.sol.read(self.fo_lines, ['procurement_id']) \
                if x['procurement_id']]
        while not_sourced:
            not_sourced = self.proxy.proc.search([
                ('id', 'in', proc_ids),
                ('state', 'not in', ('ready', 'running')),
            ])

    def get_generated_po(self):
        po_ids = set()
        self.po_lines = []
        for line in self.proxy.sol.browse(self.fo_lines):
            if line.procurement_id:
                self.po_lines.extend(self.proxy.pol.search([
                    ('procurement_id', '=', line.procurement_id.id),
                ]))

        for po_line in self.proxy.pol.read(self.po_lines, ['order_id']):
            po_ids.add(po_line['order_id'][0])

        self.po_ids = list(po_ids)

    def run_po_validation(self):
        # Add an anlytic distribution on PO lines that have no
        no_ana_line_ids = self.proxy.pol.search([
            ('order_id', 'in', self.po_ids),
            ('analytic_distribution_id', '=', False),
        ])
        self.proxy.pol.write(no_ana_line_ids, {
            'analytic_distribution_id': self._get_distrib(),
        })

        # Check if the PO is draft
        not_draft_po = self.proxy.po.search([
            ('id', 'in', self.po_ids),
            ('state', '!=', 'draft'),
        ])
        if not_draft_po:
            raise "The state of the generated PO is not 'draft'"

        self.valid_po()

    def source_lines(self):
        supp_ids = self.proxy.partner.search([
            ('supplier', '=', True),
        ])
        if not supp_ids:
            raise "No supplier found"

        self.proxy.sol.write(self.fo_lines, {
            'supplier': random.choice(supp_ids),
            'po_cft': 'po',
        })

    def valid_po(self):
        for po_id in self.po_ids:
            self.proxy.exec_workflow(
                'purchase.order',
                'purchase_confirm',
                po_id)

        return True

    def run_po_confirmation(self):
        self.proxy.po.write(self.po_ids, {
            'delivery_confirmed_date': time.strftime('%Y-%m-%d'),
        })

        po_not_confirmed = self.proxy.po.search([
            ('id', 'in', self.po_ids),
            ('state', '!=', 'confirmed'),
        ])
        if po_not_confirmed:
            raise "The state of the generated PO is not 'confirmed'"

        self.confirm_po()

    def confirm_po(self):
        for po_id in self.po_ids:
            self.proxy.po.confirm_button([po_id])

    def get_generated_in(self):
        self.in_ids = self.proxy.pick.search([
            ('type', '=', 'in'),
            ('purchase_id', 'in', self.po_ids),
        ])
        if not self.in_ids:
            raise "No IN found"

    def process_in(self):
        for incoming in self.in_ids:
            in_proc_id = self.proxy.pick.action_process([incoming])['res_id']
            self.proxy.in_proc.copy_all(in_proc_id)
            self.proxy.in_proc.do_incoming_shipment([in_proc_id])
            in_state = self.proxy.pick.read(incoming, ['state'])['state']
            while in_state != 'done':
                time.sleep(1)
                in_state = self.proxy.pick.read(incoming, ['state'])['state']

    def get_generated_out(self):
        self.out_ids = self.proxy.pick.search([
            ('type', '=', 'out'),
            ('sale_id', '=', self.fo_id),
            ('subtype', '=', 'picking'),
            ('state', '=', 'assigned'),
        ])

    def out_convert_to_standard(self):
        self.proxy.pick.convert_to_standard(self.out_ids)

    def out_processing(self):
        if self.out_ids:
            for out_id in self.out_ids:
                out_proc_id = self.proxy.pick.action_process(out_id)['res_id']
                self.proxy.out_proc.copy_all(out_proc_id)
                self.proxy.out_proc.do_partial([out_proc_id])

    def run_complete_flow(self):
        self.create_order()
        # FO validation
        self.fo_validation_chrono.measure(self.valid_fo)
        self.source_lines()
        # FO confirmation
        self.fo_confirmation_chrono.measure(self.confirm_fo)
        self.get_new_generated_fo()
        # PO creation
        self.po_creation_chrono.measure(self.run_scheduler)
        self.get_generated_po()
        # PO validation
        self.po_validation_chrono.measure(self.run_po_validation)
        # PO confirmation
        self.po_confirmation_chrono.measure(self.run_po_confirmation)
        self.get_generated_in()
        # IN processing
        self.in_processing_chrono.measure(self.process_in)
        self.get_generated_out()
        # OUT conversion
        self.out_convert_chrono.measure(self.out_convert_to_standard)
        # OUT processing
        self.out_processing_chrono.measure(self.out_processing)
