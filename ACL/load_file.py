#! /usr/bin/python
# -*- encoding: utf-8 -*-
import oerplib
import os
import sys
import time
import base64
import argparse
import csv
import yaml


parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--host", "-H", metavar="host", default="127.0.0.1", help="Host [default: %(default)s]")
parser.add_argument("--port", "-p", metavar="port", default="8070", help="NetRPC Port [default: %(default)s]")
parser.add_argument("--user", "-u", metavar="user", default="admin", help="User [default: %(default)s]")
parser.add_argument("--password", "-w", metavar="pwd", default="admin", help="Password [default: %(default)s]")
parser.add_argument("dbs_name", help="comma separated list of dbs")
parser.add_argument("yml", help="yml description of files to load")
o = parser.parse_args()

user= o.user
pwd = o.password
host = o.host
port = o.port

yaml_desc = open(o.yml, 'r')
yaml_data = yaml.load(yaml_desc)
yaml_desc.close()
prefix_file = os.path.dirname(o.yml)
for db in o.dbs_name.split(','):
    netrpc = oerplib.OERP(host, protocol='netrpc', port=port, database=db)
    netrpc.login(user, pwd)
    for data_line in yaml_data:
        for model in data_line.keys():
            filename = os.path.join(prefix_file, data_line[model])
            print 'Load %s on %s' % (filename, db)
            if model in ('product.nomenclature', 'product.category', 'product.product'):
                req = netrpc.get('res.request')
                nb = req.search([])
                wiz = self.db.get('import_data')
                f = open(filename, 'rb')
                rec_id = wiz.create({'object': model, 'file': base64.encodestring(f.read())})
                f.close()
                wiz.import_csv([rec_id], {})
                imported = False
                while not imported:
                    time.sleep(5)
                    imported = nb != req.search([])
            elif model == 'User Access':
                f = open(filename)
                data = base64.encodestring(f.read())
                f.close()
                wiz = netrpc.get('user.access.configurator')
                rec_id = wiz.create({'file_to_import_uac': data})
                wiz.do_process_uac([rec_id])
            else:
                with open(filename, 'rb') as csvfile:
                    reader = csv.reader(csvfile, delimiter=',')
                    fields = False
                    data = []
                    for row in reader:
                        if not fields:
                            fields = row
                        else:
                            data.append(row)
                    obj = netrpc.get(model)
                    if obj and fields and data:
                        obj.import_data(fields, data)
