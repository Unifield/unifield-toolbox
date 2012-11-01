# -*- encoding: utf-8 -*-
import csv
import sys
from lxml import etree
from mako.template import Template
import zipfile
import shutil
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Lib'))
import unifieldrpc
import parser

other_options = [
    (("--file", "-f"), {'metavar': 'file', 'default': 'registers_fields.ods', 'help': 'Out file [default: %(default)s]'}),
]
cmdline = parser.ArgParse(other_options)


out_file = cmdline.file
sock = unifieldrpc.Rpc(cmdline.dbname, cmdline.user, cmdline.password, cmdline.host, cmdline.port)
modeldata = 'ir.model.data'
model='ir.ui.menu'


def format_field(arch, fields, level=0):
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

    fields_tree = []
    fields_form = []
    if info['type'] in ['one2many', 'many2many']:
        editable = False
        if info.get('views', {}).get('tree', {}).get('fields'):
            arch2 = etree.fromstring(info['views']['tree']['arch'])
            tree = arch2.xpath('//tree')
            editable = tree[0].get('editable', False)
            for arch_field2 in arch2.xpath('//field'):
                    fields_tree.append(format_field(arch_field2, info['views']['tree']['fields'], level+1))
        if not editable and info.get('views', {}).get('form', {}).get('fields'):
            arch2 = etree.fromstring(info['views']['form']['arch'])
            for arch_field2 in arch2.xpath('//field'):
                    fields_form.append(format_field(arch_field2, info['views']['form']['fields'], level+1))


    attributes = []
    if info['type'] in ['one2many', 'many2many', 'many2one']:
        attributes.append('Rel: %s' % info['relation'])

    if info['type'] == 'selection':
        sel = []
        for dbkey, value in info['selection']:
            sel.append(' - %s: %s' % (dbkey, value))
        attributes.append("Selection: \n%s" % ("\n".join(sel)))
    return {
        'name': '%s%s' % (begin,field),
        'string': arch.get('string', info['string']),
        'help': arch.get('help', info.get('help', '')),
        'type': info['type'],
        'invisible': invisible,
        'readonly': readonly,
        'required': required,
        'tree': fields_tree,
        'form': fields_form,
        'attributes': attributes,
    }

helpbox = """X: Yes
C: conditional"""

headers = [
    ('Field', {}),
    ('Name', {}),
    ('Help', {}),
    ('Type', {}),
    ('Attributes', {}),
    ('Invisible', {'title': 'Invisible', 'help': helpbox}),
    ('RO', {'title': 'Read Only', 'help': helpbox}),
    ('Rq', {'title': 'Required', 'help': helpbox}),
]
ods_datas = []
xmlids = [('account', 'menu_bank_statement_tree'), ('register_accounting', 'menu_cash_register'), ('account', 'journal_cash_move_lines'), ('product', 'menu_products')]
for module, xmlid in xmlids:
    data_ids = sock.exe(modeldata, 'search', [('module', '=', module), ('name', '=', xmlid)])
    datas = sock.exe(modeldata, 'read', data_ids, ['res_id', 'model'])
    if datas[0]['model'] != 'ir.ui.menu':
        raise Exception('%s.%s : not a menu' % (module, xmlid))

    menu = sock.exe(model, 'read', datas[0]['res_id'], ['name', 'groups_id', 'action'], {'lang': 'fr_FR'})
    act, act_id = menu['action'].split(',')
    form_id = False
    action = sock.exe(act, 'read', int(act_id), ['views', 'res_model'])
    res_model = action['res_model']
    tmp_data = {
        'name': menu['name'],
        'fields': []
    }
    for views in action['views']:
        if views[1] == 'form':
            form_id = views[0]
            break

    fields_vg = sock.exe(res_model, 'fields_view_get', form_id, 'form')
    arch = etree.fromstring(fields_vg['arch'])
    for arch_field in arch.xpath('//field'):
        tmp_data['fields'].append(format_field(arch_field, fields_vg['fields']))

    ods_datas.append(tmp_data)

shutil.copyfile('template/registers_fields.ods', out_file)
zip = zipfile.ZipFile(out_file, 'a')
mytemplate = Template(filename='template/content.xml', output_encoding='utf-8', input_encoding='utf-8')
zip.writestr('content.xml', mytemplate.render(headers=headers, datas=ods_datas))
zip.close()

