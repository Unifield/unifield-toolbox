# -*- encoding: utf-8 -*-
import xmlrpclib
import csv

dbname='jfb-wm2'
user='admin'
pwd = 'admin'
port = 7069

sock = xmlrpclib.ServerProxy('http://127.0.0.1:%s/xmlrpc/common'%(port, ))
uid = sock.login(dbname, user, pwd)
sock = xmlrpclib.ServerProxy('http://127.0.0.1:%s/xmlrpc/object'%(port, ))

modeldata = 'ir.model.data'
model='ir.ui.menu'

csvf = csv.writer(open('menu.csv', 'wb'), delimiter=';',
                        quotechar='"')

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
