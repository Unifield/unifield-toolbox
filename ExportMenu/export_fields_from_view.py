# -*- encoding: utf-8 -*-
import xmlrpclib
import csv
import sys
from lxml import etree
from mako.template import Template
import zipfile
import shutil

dbname='jfb-wm2'
user='admin'
pwd = 'admin'
port = 7069
out_file = 'registers_fields.ods'

sock = xmlrpclib.ServerProxy('http://127.0.0.1:%s/xmlrpc/common'%(port, ))
uid = sock.login(dbname, user, pwd)
sock = xmlrpclib.ServerProxy('http://127.0.0.1:%s/xmlrpc/object'%(port, ))

modeldata = 'ir.model.data'
model='ir.ui.menu'





def write_fields(d, arch, fields, level=0):
    field = arch.get('name')
    info = fields[field]

    readonly = arch.get('readonly', info.get('readonly')) and 'X' or ''
    required = arch.get('required', info.get('required')) and 'X' or ''
    invisible = arch.get('invisible', info.get('invisible')) and 'X' or ''

    if arch.get('attrs'):
        attrs = eval(arch.get('attrs'))
        if 'readonly' in attrs:
            readonly = 'C'
        if 'required' in attrs:
            required = 'C'
        if 'invisible' in attrs:
            invisible = 'C'

    begin = ''
    if level:
        begin ='%s ' % ('-'*level, )

    d.append([
        '%s%s' % (begin,field),
        arch.get('string', info['string']),
        arch.get('help', info.get('help', '')),
        info['type'],
        invisible,
        readonly,
        required,
    ])


headers = ['Field', 'Name', 'Help', 'Type', 'Invisble', 'RO', 'Rq']
ods_datas = []
xmlids = [('account', 'menu_bank_statement_tree'), ('register_accounting', 'menu_cash_register'), ('account', 'journal_cash_move_lines')]
for module, xmlid in xmlids:
    tmp_data = {}
    data_ids = sock.execute(dbname, uid, pwd, modeldata, 'search', [('module', '=', module), ('name', '=', xmlid)])
    datas = sock.execute(dbname, uid, pwd, modeldata, 'read', data_ids, ['res_id', 'model'])
    if datas[0]['model'] != 'ir.ui.menu':
        raise Exception('%s.%s : not a menu' % (module, xmlid))

    menu = sock.execute(dbname, uid, pwd, model, 'read', datas[0]['res_id'], ['name', 'groups_id', 'action'], {'lang': 'fr_FR'})
    act, act_id = menu['action'].split(',')
    form_id = False
    action = sock.execute(dbname, uid, pwd, act, 'read', int(act_id), ['views', 'res_model'])
    res_model = action['res_model']
    tmp_data['name'] = menu['name']
    for views in action['views']:
        if views[1] == 'form':
            form_id = views[0]
            break
    fields_vg = sock.execute(dbname, uid, pwd, res_model, 'fields_view_get', form_id, 'form')
    arch = etree.fromstring(fields_vg['arch'])
    for arch_field in arch.xpath('//field'):
        write_fields(csvf, arch_field, fields_vg['fields'])

        info = fields_vg['fields'][arch_field.get('name')]
        if info['type'] in ('one2many', 'many2many') and info.get('views', {}).get('tree', {}).get('fields'):
            arch2 = etree.fromstring(info['views']['tree']['arch'])
            for arch_field2 in arch2.xpath('//field'):
                write_fields(csvf, arch_field2, info['views']['tree']['fields'], 1)


shutil.copyfile('template/registers_fields.ods', out_file)
zip = zipfile.ZipFile(out_file, 'a')
mytemplate = Template(filename='template/content.xml', output_encoding='utf-8', input_encoding='utf-8')
zip.writestr('content.xml', mytemplate.render(headers=headers, objects=datas)
zip.close()

