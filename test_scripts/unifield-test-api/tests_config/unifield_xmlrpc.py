'''
Created on Feb 28, 2014

@author: qt
'''

from ConfigParser import ConfigParser
from oerplib.oerp import OERP


class UnifieldTestConfigParser(ConfigParser):
    '''
    Special ConfigParser for Unifield tests battery
    '''

    def read(self, filenames=[]):
        '''
        Override readfp() method to add the config file path
        '''
        conf_file = ['../tests_config.cfg']
        return ConfigParser.read(self, conf_file)


class XMLRPCConnection(OERP):
    '''
    XML-RPC connection class to connect with OERP
    @var ana_acc: Test ana
    '''
    ana_acc = False
    distrib = False
    cc_dl = False
    partner = False
    addr = False
    location = False
    purchase = False
    po_line = False
    product = False
    sync_mgr = False
    sale = False
    sourcing_line = False
    poca = False
    picking = False
    partial_pick = False

    def __init__(self, db_suffix):
        '''
        Constructor
        '''
        config = UnifieldTestConfigParser()
        config.read()

        server_port = config.getint('Server', 'port')
        server_url = config.get('Server', 'url')
        uid = config.get('DB', 'username')
        pwd = config.get('DB', 'password')
        db_prefix = config.get('DB', 'db_prefix')

        super(XMLRPCConnection, self).__init__(
                                        server=server_url,
                                        protocol='xmlrpc',
                                        port=server_port)

        db_name = '%s%s' % (db_prefix, db_suffix)
        self.login(uid, pwd, db_name)

        self.init_objects()

    def init_objects(self):
        """
        Initialize some objects call
        """
        self.ana_acc = self.get('account.analytic.account')
        self.distrib = self.get('analytic.distribution')
        self.cc_dl = self.get('cost.center.distribution.line')
        self.partner = self.get('res.partner')
        self.addr = self.get('res.partner.address')
        self.location = self.get('stock.location')
        self.purchase = self.get('purchase.order')
        self.po_line = self.get('purchase.order.line')
        self.product = self.get('product.product')
        self.sync_mgr = self.get('sync.client.sync_manager')
        self.sale = self.get('sale.order')
        self.sourcing_line = self.get('sourcing.line')
        self.poca = self.get('procurement.order.compute.all')
        self.picking = self.get('stock.picking')
        self.partial_pick = self.get('stock.partial.picking')
