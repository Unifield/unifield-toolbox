# -*- encoding: utf-8 -*-
import csv
import psycopg2

inf = 'translation.csv'
dbname = 'jfb-wm2'

db = psycopg2.connect('dbname=%s'%dbname)
cr = db.cursor()

out = 'reject.csv'
fo = open(out, 'w')

reader = csv.reader(open(inf, "rb"),delimiter=",",quotechar='"')
writer = csv.writer(open(out, "w"), delimiter=",",quotechar='"')
#writer.writerow(['code','name','type','parent_id.complete_name'])
#seen = {}
header = reader.next()
i = 0
writer.writerow(header)
for row in reader:
    cr.execute("SELECT src, xml_id, name, res_id, module, type FROM ir_translation WHERE src = %s and lang='en_US'", (row[2], ))
    if cr.rowcount == 0:
        writer.writerow(row)
        i += 1
    for res in cr.fetchall():
        cr.execute(''' INSERT INTO ir_translation
            (src, xml_id, name, res_id, module, type, value, lang)
            values
            (%s, %s, %s, %s, %s, %s, %s, 'fr_FR')
        ''' , (res[0], res[1], res[2], res[3], res[4], res[5], row[3]))
db.commit()
cr.close()
print "%d lines rejected" % i
