#!/usr/bin/python
# -*- coding: utf-8 -*-
##############################################################################
#
#    RPC data dump module for OpenERP, fetch data and save them
#    Copyright (C) 2010 Thamini S.A. (<http://www.thamini.com>) Xavier ALT
#
#    This file is a part of RPC data dump
#
#    RPC data dump is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    RPC data dump is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


import xmlrpclib
import socket
import os
import sys
import time
import codecs
import csv
from lxml import etree
from pprint import pprint
from optparse import OptionParser


# get command line options
usage = "usage: xmlrpc-dump [options] model id1 id2 id3"
parser = OptionParser(usage=usage)
parser.add_option("-s", "--server", dest="server",
                  help='Server to connect to', default='localhost')
parser.add_option("-p", "--port", dest="port",
                  help='Which port to connect to', default=8069, type='int')
parser.add_option("-d", "--database", dest="database",
                  help='The database from where we\'re going to dump')
parser.add_option("-u", "--user", dest="user",
                  help='The user used to connect to the DB', default='admin')
parser.add_option("-w", "--password", dest="password",
                  help='The password use to connect to the DB', default='admin')
parser.add_option("-m", "--module", dest="module",
                  help='The module prefix', default=''),
parser.add_option("-o", "--output", dest="output",
                  help='The output filename, if not specified stdout is used')
parser.add_option("--save-ids", action="store_true", dest="save_ids", default=False)
parser.add_option("--sql-ids", action="store_true", dest="sql_ids", default=False)
parser.add_option("--debug", action="store_true", dest="debug", default=False)
parser.add_option("-a", "--all", dest="all", help='Take all ids', action="store_true")
parser.add_option("--without-relation", action="store_true", dest="without_relation", help="Don't take back relations. Just give normal fields")
parser.add_option("--m2o-only", action="store_true", dest="m2o_only", help="Get only many2one relations and normal fields")
parser.add_option("--m2m-only", action="store_true", dest="m2m_only", help="Get only many2many relations and normal fields")

(option, args) = parser.parse_args()

if len(args) < 2:
    if len(args) == 1 and option.all:
        print "Option 'all' choosed. Take back all elements in database for the choosen model."
    else:
        parser.print_help()
        sys.exit(2)

_logsock = xmlrpclib.ServerProxy('http://%s:%d/xmlrpc/common' % (option.server, option.port))
_userid = _logsock.login(option.database, option.user, option.password )
_sock = xmlrpclib.ServerProxy('http://%s:%d/xmlrpc/object' % (option.server, option.port))

def z_exec(model, name, *args):
    try:
        r =  _sock.execute(option.database, _userid, option.password, model, name, *args)
        return r
    except Exception, e:
        #print("RPC CALL: %s %s %s" % (model, name, (args)))
        #print("%s %s" % (e.faultCode, e.faultString))
        raise e

# indent function taken from:
# URL: http://infix.se/2007/02/06/gentlemen-indent-your-xml
# Desc: variant of indent() function found of effbotlib
#       (see http://effbot.org/zone/element-lib.htm)
# @20100716: Modified to force newline avec </record> tag
def indent(elem, level=0):
    i = "\n" + level*"    "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "    "
        for e in elem:
            indent(e, level+1)
            if not e.tail or not e.tail.strip():
                e.tail = i + "    "
                if e.tag == 'record':
                    e.tail = '\n' + e.tail
        if not e.tail or not e.tail.strip():
            e.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def get_remote_xmlid(model, id):
    domain = [('model','=',model),('res_id','=',id)]
    ids = z_exec('ir.model.data', 'search', domain)
    if not ids:
        return None
    if len(ids) > 1:
        if model == 'res.users' and id == 1:
            return 'base.user_admin' # duplicate content (base.user_admin, base.user_root)
        raise Exception("Can't get more than 1 remote xmlid for model '%s', id '%s' (%s)" % (model, id, ids))
    return '%(module)s.%(name)s' % z_exec('ir.model.data', 'read', ids[0], ['module', 'name'])

class oomodel(object):
    @classmethod
    def get_fields(cls, model, fields=[]):
        fields_info = z_exec(model, 'fields_get', fields)
        #print("FIELDS_INFO ::")
        #pprint(fields_info)
        return fields_info

    def __init__(self, model, id, fields=None, module=None):
        self.module = None
        self.model = model
        self.id = id
        self._uuid = None
        if not fields:
            self.fields = oomodel.get_fields(model)
        else:
            self.fields = fields
        self.data = z_exec(model, 'read', id, [])

    def __repr__(self):
        return u'<OO (%s, %s)>' % (self.model, self.id)

    def __getattr__(self, key):
        if key.startswith('data_'):
            return self.data[key[5:]]
        return super(oomodel, self).__getattribute__(key)

#    def get_uuid_workflow_transition(self):
#        return 'workflow_transition_%s_%s_%s' % (self.data['act_from'][1], self.data['act_to'][1], self.data['signal'])

    def get_uuid(self):
        if self._uuid:
            return self._uuid
        # try to search for existing id inside ir.model.data
        remote_xmlid = get_remote_xmlid(self.model, self.id)
        if remote_xmlid:
            return remote_xmlid
        uuid = []
        if self.module:
            uuid.append(self.module)
        uuid.append(self.model)
        try:
            spec_method = getattr(self, 'get_uuid_%s' % (self.model.replace('.','_')))
            if spec_method:
                return spec_method()
        except AttributeError:
            pass
        try:
            rec_name = z_exec(self.model, 'name_get', [self.id])
        except xmlrpclib.Fault, e:
            # TODO: Is there a better way to handle fault on name_get() call ?
            rec_name = False
        if rec_name:
            uuid.append(rec_name[0][1])
        else:
            uuid.append(self.id)
        self._uuid = ('_'.join(('%s' for x in range(len(uuid)))) % tuple(uuid)).replace('.', '_').replace(' ','_').replace('/','_').replace(',','_').replace('(','').replace(')','').encode("ascii", "ignore").lower()
        maxlength = 62-len(str(self.id))
        self._uuid = self._uuid[0:maxlength]
        self._uuid += '_%d' % (self.id)
        return self._uuid

    uuid = property(get_uuid)

    def get_base_fields(self):
        """Return non relational fields"""
        for fname in self.fields:
            if self.fields[fname]['type'] in ('boolean','char','integer','selection','text', 'float', 'date', 'datetime'):
                yield fname
        raise StopIteration

    base_fields = property(get_base_fields)

    def get_int_rel_fields(self):
        """Return M2O and M2M fields"""
        for fname in self.fields:
            if option.m2o_only:
                if self.fields[fname]['type'] in ('many2one'):
                    yield fname
            elif option.m2m_only:
                if self.fields[fname]['type'] in ('many2many'):
                    yield fname
            else:
                if self.fields[fname]['type'] in ('many2one', 'many2many'):
                    yield fname
        raise StopIteration

    int_rel_fields = property(get_int_rel_fields)

    def get_ext_rel_fields(self):
        """Return O2M fields"""
        for fname in self.fields:
            if self.fields[fname]['type'] == 'one2many':
                yield fname
        raise StopIteration

    ext_rel_fields = property(get_ext_rel_fields)


class openerp_xml_file(object):

    def __init__(self, options, module=None):
        # register options
        self.options = options
        # register module namespace
        self.module = module
        # create list of explicitly requested elements
        self.req_ids = {}
        # create empty list of tree elements
        self.xml_ids = {}
        self.xml_ids_new_only = {}
        self.xml_elements = []
        self.xml_elements_set = set()
        self.search_ids = {}

    def get_remote_xmlid(self, model, id):
        return get_remote_xmlid(model, id)

    def get_absolute_xmlid(self, value):
        if '.' not in value and self.module:
            value = '%s.%s' % (self.module, value)
        if self.module:
            module_prefix = '%s.' % (self.module)
            if value.startswith(module_prefix):
                # if one of our own resources remove absolue reference
                value = value[len(module_prefix):]
        return value


    def _search_rel(self, frel, fid):
        if (frel, fid) not in self.search_ids:
            domain = []
            extended = {}
            f_toread = []
            for f in object_search[frel]:
                if '.' in f:
                    relfield, newfield = f.split('.')
                    extended.setdefault(relfield, []).append(newfield)
                else:
                    f_toread.append(f)

            new_record = z_exec(frel, 'read', fid, f_toread+extended.keys())
            for f in f_toread:
                domain.append(('%s'%f, '=', '%s'%new_record[f]))

            if extended:
                fields_info = z_exec(frel, 'fields_get', extended.keys())
                for key in extended:
                    info = z_exec(fields_info[key]['relation'], 'read', new_record[key][0], extended[key])
                    for f in extended[key]:
                         domain.append(('%s.%s'%(key,f), '=', '%s'%info[f]))
            for i in range(0, len(domain)-1):
                domain.insert(0, '&')
            self.search_ids[(frel, fid)] = domain
        return self.search_ids[(frel, fid)]

    def dump(self, model, ids, prefix='', parent=None, ignore_xml_id=False):
        if isinstance(ids, (int,long)):
            ids = [ ids ]

        #print(">>> DUMPING: %s, %s" % (model, ids))
        model_fields = oomodel.get_fields(model, global_fields.get(model,[]))
        for id in ids:
            if not id:
                continue
            remote_xmlid = self.get_remote_xmlid(model, id)
            if remote_xmlid and ignore_xml_id:
                continue

            record = oomodel(model, id, fields=model_fields, module=self.module)
            self.req_ids[(model, record.id)] = record.uuid
            self.xml_ids[(model, record.id)] = record.uuid
            if remote_xmlid is None:
                new_xmlid = record.uuid
                if self.module:
                    new_xmlid = '%s.%s' % (self.module, new_xmlid)
                self.xml_ids_new_only[(model, record.id)] = new_xmlid

            if not option.without_relation:
                for field in record.int_rel_fields:
                    if record.data[field]:
                        # try getting xml ref
                        frel = record.fields[field]['relation']
                        if record.fields[field]['type'] == 'many2many':
                            fids = record.data[field]
                        else:
                            fids = [ record.data[field][0] ]
                        for fid in fids:
                            try:
                                rel_xmlid = self.xml_ids[(frel, fid)]
                            except KeyError:
                                # we don't currently know this resource xmlid
                                remote_xmlid = self.get_remote_xmlid(frel, fid)
                                if remote_xmlid is not None and (frel, fid) not in self.req_ids:
                                    # resource already have a remote xmlid, so we use this one
                                    self.xml_ids[(frel, fid)] = remote_xmlid
                                elif frel not in object_search:
                                    # we need to dump this resource
                                    self.dump(frel, fid)
                                elif (frel, fid) not in self.search_ids:
                                    self._search_rel(frel, fid)


            if (model, record.id) not in self.xml_ids:
                self.xml_elements.append(record)
            elif (model, record.id) in self.xml_ids and (model, record.id) in self.req_ids and (model, record.id) not in self.xml_elements_set:
                # this record was explicitely marked to be dumped
                self.xml_elements.append(record)
                self.xml_elements_set.add((model, record.id))
            elif self.module and self.xml_ids[(model, record.id)].startswith('%s.' % (self.module)):
                self.xml_elements.append(record)
                self.xml_elements_set.add((model, record.id))

            for field in record.ext_rel_fields:
                #print("::: DEBUG (EXT REL FIELD): %s" % (field))
                self.dump(record.fields[field]['relation'], record.data[field], parent=record)

    def save_to_xml(self, record):
        comment = etree.Comment("model: %s, id: %s" % (record.model, record.id))

        xml_record = etree.Element('record')
        xml_record.set('model', record.model)
        xml_record.set('id', self.get_absolute_xmlid(self.xml_ids[(record.model, record.id)]))
        for field in record.base_fields:
            fdesc = record.fields[field]
            fdata = record.data[field]
            if fdata or fdesc['type'] == 'boolean':
                felem = etree.Element('field')
                felem.set('name', field)
                if fdesc['type'] == 'boolean':
                    felem.set('eval', fdata and '1' or '0')
                else:
                    try:
                        if isinstance(fdata, (int,long,list,float)):
                            fdata = str(fdata)
                        if not isinstance(fdata, unicode):
                            fdata = unicode(fdata, 'utf-8')
                        felem.text = fdata
                    except TypeError:
                        print("Ooops with field %s: %s" % (field, record.data[field]))
                        raise
                xml_record.append(felem)
        if not option.without_relation:
            for field in record.int_rel_fields:
                fdesc = record.fields[field]
                fdata = record.data[field]
                if fdesc.get('required',False) or fdata:
                    felem = etree.Element('field')
                    felem.set('name', field)
                    def get_ref_value(relation, fid):
                        return self.get_absolute_xmlid(self.xml_ids[(relation, fid)])

                    if record.fields[field]['type'] == 'many2many':
                        if fdesc['relation'] not in object_search: 
                            felem_value = "[(6,0,[%s])]" % (','.join([ "ref('%s')" % (get_ref_value(fdesc['relation'], fid)) for fid in record.data[field] if fid]))
                            felem.set('eval', felem_value)
                        else:
                            ret = [self._search_rel(fdesc['relation'], fid) for fid in record.data[field] if fid]
                            if ret:
                                dom = ret[0]
                            for x in range(1, len(ret)):
                                dom.insert(0, '|')
                                dom += ret[x]
                                
                            felem.set('search', '%s'%dom)
                    else:
                        ref_value = u""
                        if (fdesc['relation'], fdata[0]) not in self.xml_ids and fdesc['relation'] in object_search and fdata[0]:
                            felem.set('model', fdesc['relation'])
                            felem.set('search', '%s'%self.search_ids[(fdesc['relation'], fdata[0])])
                        else:
                            if fdata and fdata[0]:
                                ref_value = get_ref_value(fdesc['relation'], fdata[0])
                            felem.set('ref', ref_value)
                    xml_record.append(felem)
        return [ comment, xml_record ]

    def save(self, filename):
        # create base xml tree
        root = etree.Element("openerp")
        data = etree.Element("data")
        root.append(data)
        if self.options.sql_ids:
            for (model, id), xmlid in self.xml_ids_new_only.iteritems():
                print("INSERT INTO ir_model_data (create_uid, write_uid, create_date, write_date, module, model, res_id, name) VALUES (%d, %d, now()::timestamp, now()::timestamp, E'%s', E'%s', %s, E'%s');" % (_userid, _userid, self.module, model, id, xmlid))
        if self.options.save_ids and self.module:
            datetime_now = time.strftime('%Y-%m-%d %H:%M:%S')
            for (model, id), xmlid in self.xml_ids_new_only.iteritems():
                z_exec('ir.model.data', 'create', {
                    'noupdate': False,
                    'module': self.module,
                    'model': model,
                    'res_id': id,
                    'name': self.get_absolute_xmlid(xmlid),
                    'date_init': datetime_now,
                    'date_update': datetime_now,
                })
        if self.options.debug:
            #print(">>> new ids ...")
            #print(self.xml_ids_new_only.values())
            #print(">>> existing ids ...")
            #print(self.xml_ids.values())
            print(">>> xml_elements ...")
            pprint(self.xml_elements)
        for record in self.xml_elements:
            new_node = self.save_to_xml(record)
            if isinstance(new_node, (list,tuple)):
                for node in new_node:
                    data.append(node)
            else:
                data.append(new_node)

        for record in self.xml_elements:
            for act in action.get(record.model,[]):
                xml_act = etree.Element('function')
                xml_act.set('model', record.model)
                xml_act.set('name', act)
                fct = etree.Element('function')
                fct.set('model', record.model)
                fct.set('name', 'search')
                fct.set("eval","[('id', '=', ref('%s'))]"%(self.xml_ids[(record.model, record.id)],))
                xml_act.append(fct)
                data.append(xml_act)


                print act
#        print(etree.tostring(root, pretty_print=True))
        indent(root)
        data = etree.tostring(root)
        if filename and filename != '-':
            print("writing output to: %s" % (filename))
            of = open(filename, 'wb')
            of.write(data)
        else:
            print(data)
#        print(etree.tostring(root))
#        print(prettyPrint(etree))


global_fields = {
    'account.analytic.account': ['name', 'code', 'parent_id', 'type', 'cost_center_ids', 'account_ids', 'category'],
    'financing.contract.donor': ['code', 'name', 'format_id', 'active'],
    'financing.contract.format.line': ['code', 'name', 'parent_id', 'line_type', 'account_ids', 'format_id', 'project_budget_value', 'project_real_value', 'overhead_percentage', 'overhead_type', 'allocated_budget_value', 'allocated_real_value'],
    'financing.contract.format' : ['format_name', 'reporting_type', 'actual_line_ids', 'cost_center_ids', 'funding_pool_ids', 'eligibility_from_date', 'eligibility_to_date'],
    'financing.contract.contract': ['code', 'donor_id', 'format_id', 'grant_amount', 'name', 'open_date', 'state', 'donor_grant_reference', 'hq_grant_reference', 'reporting_currency'],
    'purchase.order': ['warehouse_id', 'partner_ref', 'date_order', 'order_type', 'priority', 'categ', 'details', 'partner_id', 'partner_address_id', 'pricelist_id', 'origin', 'transport_mode', 'transport_cost', 'transport_currency_id', 'delivery_requested_date', 'delivery_confirmed_date', 'transport_type', 'est_transport_lead_time', 'arrival_date', 'dest_address_id', 'invoice_method', 'location_id', 'incoterm_id', 'from_yml_test'],
    'purchase.order.line': ['product_id', 'product_qty', 'product_uom', 'date_planned', 'confirmed_delivery_date', 'price_unit', 'comment', 'nomen_manda_0', 'nomen_manda_1', 'nomen_manda_2', 'nomen_manda_3', 'nomen_sub_0', 'nomen_sub_1', 'nomen_sub_2', 'nomen_sub_3', 'nomen_sub_4', 'nomen_sub_5', 'order_id', 'name'],
    'tender': ['warehouse_id', 'location_id', 'categ', 'piority', 'details', 'name', 'supplier_ids'],
    'tender.line': ['product_id', 'qty', 'product_uom', 'tender_id'],
    'sale.order': ['client_order_ref', 'order_type', 'priority', 'categ', 'details', 'partner_id', 'partner_invoice_id', 'partner_shipping_id', 'partner_order_id', 'pricelist_id', 'delivery_requested_date', 'delivery_confirmed_date', 'transport_type', 'est_transport_lead_time', 'ready_to_ship_date', 'picking_policy', 'procurement_request', 'from_yml_test'],
    'sale.order.line': ['product_id', 'product_uom_qty', 'product_uom', 'price_unit', 'discount', 'type', 'date_planned', 'confirmed_delivery_date', 'comment', 'nomen_manda_0', 'nomen_manda_1', 'nomen_manda_2', 'nomen_manda_3', 'nomen_sub_0', 'nomen_sub_1', 'nomen_sub_2', 'nomen_sub_3', 'nomen_sub_4', 'nomen_sub_5', 'order_id'],
#internal request
    'stock.inventory': ['name'],
    'stock.inventory.line': ['product_id', 'product_uom', 'product_qty', 'location_id', 'reason_type_id', 'comment', 'hidden_perishable_mandatory', 'hidden_batch_management_mandatory', 'prod_lot_id', 'expiry_date', 'type_check', 'inventory_id'],
    'stock.production.lot': ['product_id', 'name', 'type', 'date', 'life_date'],
    'stock.picking': ['origin', 'reason_type_id', 'type', 'move_lines', 'state', 'from_yml_test'],
    'stock.move': ['product_id', 'location_id', 'location_dest_id', 'product_uom', 'reason_type_id', 'product_qty', 'prodlot_id', 'expired_date', 'state', 'name'],
}

object_search = {
    'product.product': ['default_code', 'name'],
    'res.partner': ['name', 'ref'],
    'res.partner.address': ['partner_id.name', 'partner_id.ref', 'type'],
}

domain = {'sale.order': [('procurement_request', 'in', ('t','f'))]}

action = {
    'stock.inventory': ['action_confirm', 'action_done']
}
oxf = openerp_xml_file(option, option.module)
# supply:
#   ./blk_xmlrpc-dump.py  -d jfb_data_supply_magali -a purchase.order purchase.order.line tender tender.line sale.order sale.order.line stock.production.lot stock.inventory stock.inventory.line stock.picking --output /tmp/out.xml

for model in args:
    ids = z_exec(model, 'search', domain.get(model, []))
    print model, ids
    total = 0
    for id in ids:
        oxf.dump(model, int(id), ignore_xml_id=True)
        total += 1
oxf.save(option.output)
