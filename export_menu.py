# -*- encoding: utf-8 -*-
import xmlrpclib
import csv

dbname='dev-sprint5-rc1'
user='admin'
pwd = '4unifield'

sock = xmlrpclib.ServerProxy('http://127.0.0.1:8069/xmlrpc/common')
uid = sock.login(dbname, user, pwd)
sock = xmlrpclib.ServerProxy('http://127.0.0.1:8069/xmlrpc/object')

modeldata = 'ir.model.data'
model='ir.ui.menu'

csvf = csv.writer(open('menu.csv', 'wb'), delimiter=';',
                        quotechar='"')

groups_id = sock.execute(dbname, uid, pwd, 'res.groups','search',[('name','!=','Tempo')])
groups=[]
for group in sock.execute(dbname, uid, pwd, 'res.groups','read',groups_id,['name']):
    groups.append( (group['id'],group['name']) )

csvf.writerow(['module','xml_id','Level','Name']+[x[1] for x in groups])

def printlevel(parent=False, level=0,groupherit=[]):
    ids = sock.execute(dbname, uid, pwd, model, 'search',[('parent_id','=', parent)])
    if ids:
       for m in  sock.execute(dbname, uid, pwd, model, 'read',ids,['name','groups_id'],{'lang': 'fr_FR'}):
        rids = sock.execute(dbname, uid, pwd, modeldata, 'search', [('res_id', '=', m['id']), ('model','=',model)])
        data = sock.execute(dbname, uid, pwd, modeldata, 'read', rids[0], ['name','module'])
        add = []
        for g in groups:
            if g[0] in m['groups_id']:
                add.append(g[1])
            #elif g[0] in groupherit:
            #    add.append("(%s)"%g[1])
            else:
                add.append('')

        csvf.writerow([data['module'],data['name'],'+'*level,m['name'].encode('utf8')]+add)
        printlevel(m['id'], level+1, m['groups_id'] or groupherit)

printlevel()

#print sock.execute(dbname, uid, pwd, 'res.partner', [])
#print ids
#print sock.execute(dbname, uid, pwd, model, 'perm_read', [1],['write_date'])
#print sock.execute(dbname, uid, pwd, model, 'read', [1],['content'])[0]['content']

#print sock.execute(dbname, uid, pwd, model, 'read',ids,[date])
