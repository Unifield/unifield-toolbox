# -*- coding: utf-8 -*-


import random
import yaml
import os
import csv
import time

#from test_proxy import TestProxy
from supply_flow import POFromScratchTestCase
from supply_flow import POFromFOTestCase
from supply_flow import POFromInternalIRTestCase
from supply_flow import POFromExternalIRTestCase
from supply_flow import POFromFOTenderTestCase
from supply_flow import POFromIRTenderTestCase
from supply_flow import FOFromStockTestCase
from supply_flow import InternalIRFromStockTestCase
from supply_flow import ExternalIRFromStockTestCase
from supply_flow import FOFromStockOnOrderTestCase
from supply_flow import InitialInventoryTestCase
from supply_flow import PhysicalInventoryTestCase
from supply_flow import ConsumptionReportTestCase
from supply_flow import SupplyTestChrono


class YamlSupplyTestCase(object):

    cases = []

    @classmethod
    def get_cases_from_file(cls, file_to_check):
        """
        """
        if not os.path.exists(file_to_check):
            file_to_check = '%s/%s' % (
                    os.path.dirname(os.path.abspath(__file__)),
                    file_to_check,)

        try:
            stream = open(file_to_check, 'r')
            yml_res = yaml.load(stream)

            name = ''
            for i in yml_res:
                if isinstance(i, dict):
                    cls.cases.append(YamlSupplyTestCase(name, i))
                    name = ''
                elif i:
                    name += i
        except IOError as e:
            print 'The script failed because no YAML file found !'

    def __init__(self, name, values):
        self.name = name

        # Model
        if not values.get('model'):
            raise ValueError(
                'The \'model\' of the YamlTestCase is not defined',
            )
        self.model = values.get('model')

        # Qty per month (default: 1)
        self.qty_per_month = values.get('qty_per_month', 1)
        # Number of lines (default: 1)
        self.nb_lines = values.get('nb_lines', 1)
        # Percentage of service products (default: 0)
        self.service_products = values.get('service_products', 0)
        # Percentage of BM/ED products (default: 0)
        self.bm_products = values.get('bm_products', 0)
        # Percentage of received IN (default: 100)
        self.received = values.get('received', 100)
        # Percentage of backordered IR (default: 0)
        self.backordered = values.get('backordered', 0)
        # Percentage of IN that generates two backorders (default: 0)
        self.two_backorders = values.get('two_backorders', 0)

        # IR type (must be set if model='internal.request' −
        # Possible values: 'internal' / 'external')
        if self.model == 'internal.request' and not values.get('ir_type'):
            raise ValueError(
                """The 'ir_type' must be defined if 'model' is
 'internal.request'""",
            )
        self.ir_type = values.get('ir_type', None)

        # Percentage of medical POs (default: 0)
        self.med_po = values.get('med_po', 0)
        # Percentage of logistic POs (default: 0)
        self.log_po = values.get('log_po', 0)
        # Percentage of other POs (default: 100)
        self.other_po = values.get('other_po', 100)
        # Check that these three parameters are equal to 100%
        if (self.med_po + self.log_po + self.other_po) != 100:
            raise ValueError(
                """The sum of the three parameters 'med_po', 'log_po' and
 'other_po' must be equal to 100."""
            )

        # Percentage of emergency POs (default: 0)
        self.emergency_po = values.get('emergency_po', 0)
        # Percentage of normal POs (default: 100)
        self.normal_po = values.get('normal_po', 100)
        # Check that these two parameters are equal to 100%
        if (self.emergency_po + self.normal_po) != 100:
            raise ValueError(
                """The sum of the two parameters 'emergency_po' and
 'normal_po' must be equal to 100."""
            )

        # Percentage of picked Picking tickets (default: 0)
        self.picked = values.get('picked', 0)
        # Percentgae of packed PPL (default: 0)
        self.packed = values.get('packed', 0)
        # Percentage of shipped shipments (default: 0)
        self.shipped = values.get('shipped', 0)
        # Percentage of delivered OUT (default: 0)
        self.delivered = values.get('delivered', 0)

        # Is the FO/IR sourced by a tender (default: False)
        self.with_tender = values.get('with_tender', False)
        # Min. number of lines in the FO sourced by tender (default: 1)
        self.min_lines = values.get('min_lines', 1)
        # Max. number of lines in the FO sourced by tender (default: 20)
        self.max_lines = values.get('max_lines', 20)
        # Min. number of suppliers in the tender (default: 3)
        self.min_supplier = values.get('min_supplier', 3)
        # Max. number of suppliers in the tender (default: 6)
        self.max_supplier = values.get('max_supplier', 6)

        # Percentage of order lines sourced from stock (default: 0)
        self.from_stock = values.get('from_stock', 0)

        # Percentage of MED. FO (default: 0)
        self.med_fo = values.get('med_fo', 0)
        # Percentage of LOG FO (default: 0)
        self.log_fo = values.get('log_fo', 0)
        # Percentage of other FO (default: 100)
        self.other_fo = values.get('other_fo', 100)
        # Check that these three parameters are equal to 100%
        if (self.med_fo + self.log_fo + self.other_fo) != 100:
            raise ValueError(
                """The sum of the three parameters 'med_fo', 'log_fo' and
 'other_fo' must be equal to 100."""
            )

        # Percentage of emergency FOs (default: 0)
        self.emergency_fo = values.get('emergency_fo', 0)
        # Percentage of normal FOs (default: 100)
        self.normal_fo = values.get('normal_fo', 100)
        # Check that these two parameters are equal to 100%
        if (self.emergency_fo + self.normal_fo) != 100:
            raise ValueError(
                """The sum of the two parameters 'emergency_fo' and
 'normal_fo' must be equal to 100."""
            )
        # Use consumption unit
        self.use_cu = values.get('use_cu', False)

    def __repr__(self):
        return """
        Name of the case: %(name)s
        Model: %(model)s
        Qty. per month: %(qty_per_month)s
        # of lines in the order: %(nb_lines)s
        %% of service products: %(service_products)s
        %% of BM/ED products: %(bm_products)s
        %% of IN received: %(received)s
        %% of BO of IN received: %(backordered)s
        %% of IN received that make 2 BO: %(two_backorders)s
        Type of the IR: %(ir_type)s
        %% of MED PO: %(med_po)s
        %% of LOG PO: %(log_po)s
        %% of Other PO: %(other_po)s
        %% of Emergency PO: %(emergency_po)s
        %% of Normal PO: %(normal_po)s
        %% of Picked Picking Tickets: %(picked)s
        %% of Packed PPL: %(packed)s
        %% of Shipped Shipments: %(shipped)s
        %% of OUT delivered: %(delivered)s
        FO sourced by a tender: %(with_tender)s
        Min. suppliers on tender: %(min_supplier)s
        Max. suppliers on tender: %(max_supplier)s
        Min. lines on tender: %(min_lines)s
        Max. lines on tender: %(max_lines)s
        %% of IR/FO lines sourced from stock: %(from_stock)s
        %% of MED FO: %(med_fo)s
        %% of LOG FO: %(log_fo)s
        %% of Other FO: %(other_fo)s
        %% of Emergency FO: %(emergency_fo)s
        %% of Normal FO: %(normal_fo)s
        Use Consumption Unit: %(use_cu)s
        """ % {
            'name': self.name,
            'model': self.model,
            'qty_per_month': self.qty_per_month,
            'nb_lines': self.nb_lines,
            'service_products': self.service_products,
            'bm_products': self.bm_products,
            'received': self.received,
            'backordered': self.backordered,
            'two_backorders': self.two_backorders,
            'ir_type': self.ir_type,
            'med_po': self.med_po,
            'log_po': self.log_po,
            'other_po': self.other_po,
            'emergency_po': self.emergency_po,
            'normal_po': self.normal_po,
            'picked': self.picked,
            'packed': self.packed,
            'shipped': self.shipped,
            'delivered': self.delivered,
            'with_tender': self.with_tender,
            'min_supplier': self.min_supplier,
            'max_supplier': self.max_supplier,
            'min_lines': self.min_lines,
            'max_lines': self.max_lines,
            'from_stock': self.from_stock,
            'med_fo': self.med_fo,
            'log_fo': self.log_fo,
            'other_fo': self.other_fo,
            'emergency_fo': self.emergency_fo,
            'normal_fo': self.normal_fo,
            'use_cu': self.use_cu,
        }

    def run(self, proxy, month=None):
        """
        Run the case
        """
        tc = None
        if self.model == 'purchase.order':
            tc = POFromScratchTestCase(proxy, self)
        elif self.model == 'field.order':
            if self.with_tender:
                tc = POFromFOTenderTestCase(proxy, self)
            elif self.from_stock == 100:
                tc = FOFromStockTestCase(proxy, self)
            elif 0 < self.from_stock < 100:
                tc = FOFromStockOnOrderTestCase(proxy, self)
            else:
                tc = POFromFOTestCase(proxy, self)
        elif self.model == 'internal.request':
            if self.with_tender:
                tc = POFromIRTenderTestCase(proxy, self)
            elif self.ir_type == 'external':
                if self.from_stock == 100:
                    tc = ExternalIRFromStockTestCase
                else:
                    tc = POFromExternalIRTestCase(proxy, self)
            elif self.ir_type == 'internal':
                if self.from_stock == 100:
                    tc = InternalIRFromStockTestCase(proxy, self)
                else:
                    tc = POFromInternalIRTestCase(proxy, self)
        elif self.model == 'initial.stock.inventory':
            tc = InitialInventoryTestCase(proxy, self)
        elif self.model == 'stock.inventory':
            tc = PhysicalInventoryTestCase(proxy, self)
        elif self.model == 'consumption.report':
            tc = ConsumptionReportTestCase(proxy, self)
        else:
            raise NotImplemented('Not implemented yet !')

        if tc is not None:
            tc.run(month)

def start_supply_cases(proxy):
    YamlSupplyTestCase.get_cases_from_file('supply_cases.yml')
    months = [
        '2014-01',
        '2014-02',
        '2014-03',
        '2014-04',
        '2014-05',
        '2014-06',
        '2014-07',
        '2014-08',
        '2014-09',
        '2014-10',
        '2014-11',
        '2014-12',
        '2015-01',
        '2015-02',
        '2015-03',
        '2015-04',
        '2015-05',
        '2015-06',
        '2015-07',
        '2015-08',
        '2015-09',
        '2015-10',
        '2015-11',
        '2015-12',
    ]

    for month in months:
        print '###############################################################'
        print '#'
        print '# Month: %s' % month
        print '#'

        for tc in YamlSupplyTestCase.cases:
            print '# Test case: %s' % tc.name
            print '# Start time: %s' % time.strftime('%Y-%m-%d %H:%M:%S')
            tc.run(proxy, month)
            print '# End time: %s' % time.strftime('%Y-%m-%d %H:%M:%S')
            print '#'
            print '######################################'
            print '#'

    report_path = '%s/supply_case.csv' % (
        os.path.dirname(os.path.abspath(__file__)), )
    with open(report_path, 'wb') as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=',',
            quoting=csv.QUOTE_MINIMAL)

        for cc, cc_cases in SupplyTestChrono.cases.iteritems():
            csv_writer.writerow([
                'Name',
                'Date',
                'FO Validation',
                'FO Confirmation',
                'PO Creation',
                'PO Validation',
                'PO Confirmation',
                'IN Processing',
                'OUT Convert',
                'OUT Processing',
                'PICK Processing',
                'PACK Processing',
                'SHIP Processing',
            ])
            for chrono in cc_cases:
                csv_writer.writerow([
                    cc,
                    chrono.date,
                    chrono.valid_fo.process_time,
                    chrono.confirm_fo.process_time,
                    chrono.po_creation.process_time,
                    chrono.valid_po.process_time,
                    chrono.confirm_po.process_time,
                    chrono.process_in.process_time,
                    chrono.convert_out.process_time,
                    chrono.process_out.process_time,
                    chrono.process_pick.process_time,
                    chrono.process_pack.process_time,
                    chrono.process_ship.process_time,
                ])

            csv_writer.writerow([
                '###',
                '###',
                '###',
                '###',
                '###',
                '###',
                '###',
                '###',
                '###',
                '###',
                '###',
                '###',
            ])  

        csv_file.close()
