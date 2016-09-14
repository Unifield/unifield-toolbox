#! /usr/bin/python

import xmlrpclib
import psycopg2
import sys
import os
import csv

db_prefix = 'jfb-trans-unidata_'
for DBS in [
        ['OCBHQ_1209_1923_1', 'OCBHT101_1209_1806'],
        ['OCBHQ_1209_1923_1', 'OCBHT143_1009_1804_1'],
        ['OCBHQ_1209_1923_1', 'OCBHT118_1209_1906'],
        ['OCG_HQ_1109_0015', 'OCG_CM1_KSR_1009_2201'],
        ['OCG_HQ_1109_0015', 'OCG_CM1_COO_1109_0411'],
        ['OCG_HQ_1109_0015', 'OCG_CM1_MRA-20160913'],
        ]:
    for LANG in ('en_MF', 'fr_MF'):
        seen = False
        to_complete = {}
        file_out = '/tmp/diff_trans_%s_%s_%s.csv' % (DBS[0], DBS[1], LANG, )
        p = open(file_out, 'w')
        writer = csv.writer(p, delimiter=',', quoting=csv.QUOTE_ALL)
        for dbname in DBS:
            if db_prefix:
                dbname = '%s%s' %(db_prefix, dbname)
            dsn='dbname=%s' % dbname
            db = psycopg2.connect(dsn)
            cr = db.cursor()
            # get product xmlid
            query = "select res_id,name from ir_model_data where model='product.product' and module='sd'"
            if not seen:
                xmlid = {}
                cr.execute(query)
                for x in cr.fetchall():
                    xmlid[x[0]] = x[1]

                query = """select p.id, d.name, trans.xml_id from product_product p
                    left join ir_model_data d on d.res_id=p.id and d.model='product.product' and module='sd'
                    left join ir_translation trans on trans.res_id = p.product_tmpl_id and trans.name='product.template,name'
                    where trans.lang=%s and trans.xml_id != d.name"""
                cr.execute(query, (LANG, ))
                wrong_xmlid_intrans = {}
                for x in cr.fetchall():
                    wrong_xmlid_intrans[x[0]] = x

            #query = """SELECT default_code, product_template.name AS value, product_product.product_tmpl_id, product_template.id, ir_translation.id
            query = """SELECT default_code, COALESCE(ir_translation.value,product_template.name) AS value, product_product.id, product_template.id, ir_translation.id, product_international_status.name
        FROM product_product
        INNER JOIN product_international_status ON product_product.international_status = product_international_status.id
        INNER JOIN product_template ON product_product.product_tmpl_id = product_template.id
        LEFT JOIN ir_translation ON ir_translation.res_id = product_template.id AND ir_translation.lang = %s AND ir_translation.name = 'product.template,name'
        WHERE active = 't' AND international_status != 4
        ORDER BY default_code DESC
        """
            cr.execute(query, (LANG, ))
            nbdiff = 0

            if seen:
                writer.writerow(['db1: %s' % DBS[0]])
                writer.writerow(['db2: %s' % DBS[1]])
                writer.writerow(['Default Code', 'Desc db1', 'Desc db2', 'Prod id db1', 'Tmpl id db1', 'Trans id db1', 'Prod id db2', 'Tmpl id db2', 'Trans id db2', 'Prod sdref', 'Prod type', 'Issue'])
            for x in cr.fetchall():
                if not seen:
                    if x[0] in to_complete:
                        print 'duplicated', x[0]
                        raise
                    to_complete[x[0]] = x
                else:
                    if x[0] not in to_complete:
                        continue
                        print 'Absent %s %s' % x
                    elif to_complete[x[0]][1] != x[1]:
                        nbdiff += 1
                        issue = ""
                        # not trans on 2nd instance
                        if to_complete[x[0]][2] in wrong_xmlid_intrans:
                            issue ='wrong xmlid in trans'
                        elif x[4] and not to_complete[x[0]][4]:
                            issue = 'translation on db2 not on db1'
                        writer.writerow([x[0], to_complete[x[0]][1], x[1], to_complete[x[0]][2], to_complete[x[0]][3], to_complete[x[0]][4], x[2], x[3], x[4], xmlid.get(to_complete[x[0]][2]), x[5], issue])

            if seen:
                print "Nb nbdiff %s, %s" % (nbdiff, file_out)
            seen = True

            cr.close()
        p.close()
sys.exit(1)
