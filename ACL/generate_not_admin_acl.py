# -*- encoding: utf-8 -*-


"""
This script generates ir.model.access.csv file from a list of Object Name given in a csv file
see: UF-2341
"""
import csv
import psycopg2

dbname = 'pilot30b2-pre_SYNC_SERVER-jfb2'
input_file = 'obj_notadmin_read.csv'
db = psycopg2.connect("dbname=%s" % dbname)
cr = db.cursor()

reader = csv.reader(open(input_file, "rb"),delimiter=",",quotechar='"')
print '"id","name","model_id:id","group_id:id","perm_read","perm_write","perm_create","perm_unlink"'
for row in reader:
    cr.execute("""
        select d.module, m.model from ir_model m
        left join ir_model_data d on d.model='ir.model' and d.res_id = m.id
        where m.name=%s
    """, (row[0], ))
    resu = cr.fetchall()
    if not resu or not resu[0]:
        raise Exception(row[0])
    model = resu[0][1]
    module = resu[0][0]
    model_under = model.replace('.', '_')
    print '"access_%(model_under)s","admin access %(name)s","%(module)s.model_%(model_under)s","base.group_erp_manager",1,1,1,1' % {'model_under': model_under, 'name': row[0], 'module': module}
