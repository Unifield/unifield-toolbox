# -*- encoding: utf-8 -*-
import xmlrpclib
import csv
import sys
from lxml import etree


dbname='jfb-wm2'
user='admin'
pwd = 'admin'
port = 7069

sock = xmlrpclib.ServerProxy('http://127.0.0.1:%s/xmlrpc/common'%(port, ))
uid = sock.login(dbname, user, pwd)
sock = xmlrpclib.ServerProxy('http://127.0.0.1:%s/xmlrpc/object'%(port, ))

modeldata = 'ir.model.data'
model='ir.ui.menu'


csvf = csv.writer(open('menu.csv', 'wb'), delimiter=';', quotechar='"')
csvf.writerow(['Field', 'Name', 'Help', 'Type', 'Attributes', 'RO', 'Rq'])
xmlids = [('account', 'menu_bank_statement_tree'), ('register_accounting', 'menu_cash_register'), ('account', 'journal_cash_move_lines')]
for module, xmlid in xmlids:
    data_ids = sock.execute(dbname, uid, pwd, modeldata, 'search', [('module', '=', module), ('name', '=', xmlid)])
    datas = sock.execute(dbname, uid, pwd, modeldata, 'read', data_ids, ['res_id', 'model'])
    if datas[0]['model'] != 'ir.ui.menu':
        raise Exception('%s.%s : not a menu' % (module, xmlid))

    menu = sock.execute(dbname, uid, pwd, model, 'read', datas[0]['res_id'], ['name', 'groups_id', 'action'], {'lang': 'fr_FR'})
    act, act_id = menu['action'].split(',')
    form_id = False
    action = sock.execute(dbname, uid, pwd, act, 'read', int(act_id), ['views', 'res_model'])
    res_model = action['res_model']
    csvf.writerow([menu['name']])
    for views in action['views']:
        if views[1] == 'form':
            form_id = views[0]
            break
    fields_vg = sock.execute(dbname, uid, pwd, res_model, 'fields_view_get', form_id, 'form')
    arch = etree.fromstring(fields_vg['arch'])
    for arch_field in arch.xpath('//field'):
        field = arch_field.get('name')
        info = fields_vg['fields'][field]
    #for field, info in fields_vg['fields'].iteritems():
        if arch_field.get('readonly'):
            readonly = arch_field.get('readonly')
        else:
            readonly = info.get('readonly')
        if arch_field.get('required'):
            required = arch_field.get('required')
        else:
            required = info.get('required')
        csvf.writerow([field, arch_field.get('string', info['string']), arch_field.get('help', info.get('help')), info['type'], '', readonly and 'X' or '', required and 'X' or ''])
        if info['type'] in ('one2many', 'many2many') and info.get('views', {}).get('tree', {}).get('fields'):
            arch2 = etree.fromstring(info['views']['tree']['arch'])
            for arch_field2 in arch2.xpath('//field'):
                field1 = arch_field2.get('name')
                info1 = info['views']['tree']['fields'][field1]
                
                csvf.writerow(['-- %s'%field1, arch_field2.get('string', info1['string']), arch_field2.get('help', info1.get('help', '')), info1['type'], '', arch_field2.get('readonly', info1.get('readonly')) and 'X' or '', arch_field2.get('required', info1.get('required')) and 'X' or ''])






sys.exit(1)
groups_id = sock.execute(dbname, uid, pwd, 'res.groups','search',[('name','!=','Tempo')])
groups=[]
for group in sock.execute(dbname, uid, pwd, 'res.groups','read',groups_id,['name']):
    groups.append( (group['id'],group['name']) )

csvf.writerow(['module','xml_id','Level','Name', 'Object', 'Technical object name']+[x[1] for x in groups])

cache_obj = {}
def printlevel(parent=False, level=0,groupherit=[]):
    ids = sock.execute(dbname, uid, pwd, model, 'search',[('parent_id','=', parent)])
    if ids:
       for m in  sock.execute(dbname, uid, pwd, model, 'read', ids, ['name', 'groups_id', 'action'], {'lang': 'fr_FR'}):
        rids = sock.execute(dbname, uid, pwd, modeldata, 'search', [('res_id', '=', m['id']), ('model', '=', model)])
        data = sock.execute(dbname, uid, pwd, modeldata, 'read', rids[0], ['name', 'module'])
        # search action
        human_obj = ''
        technical_obj = ''
        if m['action']:
            act_type, action_id = m['action'].split(',')
            if act_type != 'ir.actions.server':
                new_obj = sock.execute(dbname, uid, pwd, act_type, 'read', [action_id], ['res_model'])[0]
                technical_obj = new_obj['res_model']
                if technical_obj not in cache_obj:
                    model_ids = sock.execute(dbname, uid, pwd, 'ir.model', 'search', [('model', '=', technical_obj)])
                    cache_obj[new_obj['res_model']] = sock.execute(dbname, uid, pwd, 'ir.model', 'read', model_ids[0], ['name'])['name']
                human_obj = cache_obj[technical_obj]
            else:
                human_obj = sock.execute(dbname, uid, pwd, act_type, 'read', [action_id], ['name'])[0]['name']

        add = []
        for g in groups:
            if g[0] in m['groups_id']:
                add.append(g[1])
            #elif g[0] in groupherit:
            #    add.append("(%s)"%g[1])
            else:
                add.append('')

        csvf.writerow([data['module'],data['name'],'+'*level,m['name'].encode('utf8'), human_obj, technical_obj]+add)
        printlevel(m['id'], level+1, m['groups_id'] or groupherit)

printlevel()

#print sock.execute(dbname, uid, pwd, 'res.partner', [])
#print ids
#print sock.execute(dbname, uid, pwd, model, 'perm_read', [1],['write_date'])
#print sock.execute(dbname, uid, pwd, model, 'read', [1],['content'])[0]['content']

#print sock.execute(dbname, uid, pwd, model, 'read',ids,[date])
