# -*- coding: utf-8 -*-

from ConfigParser import ConfigParser
from ConfigParser import NoSectionError
from ConfigParser import NoOptionError
from oerplib import OERP

from finance_flow import FinanceSetup
from finance_flow import FinanceMassGen
from finance_flow import FinanceFlow

import logging
import time
import os
import sys

MODELS = {
    'ir_data': 'ir.model.data',
    'comp': 'res.company',
    'fy': 'account.fiscalyear',
    'per': 'account.period',
    'per_cr': 'account.period.create',
    'ccy': 'res.currency',
    'so': 'sale.order',
    'sol': 'sale.order.line',
    'po': 'purchase.order',
    'pol': 'purchase.order.line',
    'data': 'ir.model.data',
    'pick': 'stock.picking',
    'ship': 'shipment',
    'move': 'stock.move',
    'prod': 'product.product',
    'ana_acc': 'account.analytic.account',
    'ad': 'analytic.distribution',
    'cc': 'cost.center.distribution.line',
    'fp': 'funding.pool.distribution.line',
    'acc_type': 'account.account.type',
    'acc': 'account.account',
    'acc_type': 'account.account.type',
    'journal': 'account.journal',
    'ana_journal': 'account.analytic.journal',
    'partner': 'res.partner',
    'emp': 'hr.employee',
    'addr': 'res.partner.address',
    'proc': 'procurement.order',
    'out_proc': 'outgoing.delivery.processor',
    'in_proc': 'stock.incoming.processor',
    'in_proc_move': 'stock.move.in.processor',
    'lot': 'stock.production.lot',
    'pt_proc': 'create.picking.processor',
    'ptl_proc': 'create.picking.move.processor',
    'vpt_proc': 'validate.picking.processor',
    'ppl_proc': 'ppl.processor',
    'ship_proc': 'shipment.processor',
    'ppl_family': 'ppl.family.processor',
    'inventory': 'stock.inventory',
    'inventory_line': 'stock.inventory.line',
    'ini_inv': 'initial.stock.inventory',
    'ini_inv_line': 'initial.stock.inventory.line',
    'loc': 'stock.location',
    'tender': 'tender',
    'tender_line': 'tender.line',
    'reg': 'account.bank.statement',
    'reg_cr': 'wizard.register.creation',
    'regl': 'account.bank.statement.line',
    'am': 'account.move',
    'aml': 'account.move.line',
    'inv': 'account.invoice',
    'inv_imp': 'wizard.import.invoice',
    'inv_imp_l': 'wizard.import.invoice.lines',
    'acc_dest_link': 'account.destination.link',
    'rac': 'real.average.consumption',
    'racl': 'real.average.consumption.line',
}

_COLORS = {
    'normal': '\033[0;39m',
    'blue': '\033[1;34m',
    'green': '\033[1;32m',
    'magenta': '\033[1;35m',
    'red': '\033[1;31m',
    'yellow': '\033[1;33m',
}

def color_str(msg, color_code):
    """
    color message
    :param msg: message
    :param color_code: color code
    :return:
    """
    return "%s%s%s" % (_COLORS[color_code], msg, _COLORS['normal'], )


class TestProxy(object):

    def __init__(self, config_file=None):
        # Read config file
        if not config_file:
            config_file = '%s/test_perf.cfg' % (
                os.path.dirname(os.path.abspath(__file__)),
            )
        self.read_cfg_file(config_file)

        try:
            logfile_path = self.config.get('logging', 'logfile')
        except (NoSectionError, NoOptionError) as e:
            logfile_path = '%s/test_perf.log' % (
                os.path.dirname(os.path.abspath(__file__)),
            )

        logging.basicConfig(
            filename= logfile_path,
            level=logging.INFO,
            format='%(message)s',
        )

        self.min_lines = self.config.getint('supply', 'min_lines')
        self.max_lines = self.config.getint('supply', 'max_lines')

        # Prepare connection data
        server_port = self.config.getint('server', 'port')
        server_url = self.config.get('server', 'url')
        uid = self.config.get('database', 'username')
        pwd = self.config.get('database', 'password')
        db_name = self.config.get('database', 'name')

        # Unifield connection
        self.conn = OERP(
            server=server_url,
            protocol='xmlrpc',
            port=server_port,
            timeout=3600,
        )
        # Unifield login
        self.login = self.conn.login(uid, pwd, db_name)

        # Prepare objects proxies
        for key, model in MODELS.iteritems():
            if not hasattr(self, key):
                setattr(self, key, self.get(model))

        self.product_ids = self.prod.search([
            ('type', '=', 'product'),
            ('batch_management', '=', False),
            ('perishable', '=', False),
        ])
        
    def get(self, model):
        """
        get oerplib model
        :param model: model name
        :type model: str
        """
        return self.conn.get(model)

    def read_cfg_file(self, config_file):
        """
        Read the configuration file
        :param config_file: Path to the config file
        :return: True
        """
        if not os.path.exists(config_file):
            raise NameError('%s not found !' % config_file)

        if not hasattr(self, 'config'):
            self.config = ConfigParser()
        self.config.read([config_file])

        return True

    def log(self, msg, color_code=None):
        """
        Write the message in log file (optionaly, color it)
        :param msg: The message to log
        :param color_code: Code of the color to use (optional)
        :return: True
        """
        msg = '%s :: %s' % (
            time.strftime('%Y-%M-%d %H:%M:%S'),
            msg,
        )

        logging.info(msg)  # log without color
        if color_code:
            msg = color_str(msg, color_code)
        print msg
        return True

    def exec_workflow(self, *args):
        self.conn.exec_workflow(*args)

    def current_date2orm(self):
        """
        get current date
        :rtype: str YYYY-MM-DD
        """
        return time.strftime('%Y-%m-%d')

    def date2orm(self, dt):
        """
        convert date to orm format
        :type dt: DateTime
        :rtype: str YYYY-MM-DD
        """
        return dt.strftime('%Y-%m-%d')
        
    def random_date(start, end):
        """
        :type start: datetime
        :type end: datetime
        :return: a random datetime between two datetime
        :rtype: datetime
        """
        # http://stackoverflow.com/questions/553303/generate-a-random-date-between-two-other-dates
        delta = end - start
        int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
        random_second = randrange(int_delta)
        return (start + timedelta(seconds=random_second))

    def get_iter_item(self, iter, index):
        """
        get iterable item at given index
        used to get a specific item of an oerplib browsed list's item
        :param iter: iterable to get item from
        :param index: index of the wanted item
        :type index: int
        :return item or None
        """
        i = 0
        for item in iter:
            if i == index:
                return item
            i += 1
        return None

    def get_record_id_from_xmlid(self, module, xmlid):
        """
        get record id from xml id
        :param module: module name
        :type module: str
        :param xmlid: xmlid
        :type xmlid: str
        :return: id
        """
        obj = self.ir_data.get_object_reference(module, xmlid)
        return obj[1] if obj else False

    def hook_invoice(self, invoice_id):
        return


if __name__ == '__main__':
    args = sys.argv[1:]  # skip this script
    command = args and args[0] or False
    
    proxy = TestProxy()

    FinanceSetup(proxy).run()
    if command in ('finance_je', 'finance_reg', ):
        FinanceMassGen(proxy).run(command)

    """supply_test = SupplyFlow(proxy)
    supply_test.run_complete_flow()"""

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4
