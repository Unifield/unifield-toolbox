# -*- encoding: utf-8 -*-
import xmlrpclib
import os
import sys
import time
import base64

user='admin'
pwd = 'admin'

# xmlrpc port
port = 8069
#host = '10.0.0.174'
host = '127.0.0.1'

if len(sys.argv) < 2:
    print "%s backup_dir" % (sys.argv[0], )
    sys.exit(0)

target_dir = sys.argv[1]
if os.path.exists(target_dir):
    if os.listdir(target_dir) != []:
        print "Dir %s not empty" % (target_dir, )
        sys.exit(0)
else:
    os.mkdir(target_dir)

sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/db'%(host, port))
for db in sock.list():
    print db
    dump = sock.dump(pwd, db)
    db_dump = os.path.join(target_dir, '%s-%s.dump' % (db, time.strftime('%Y%m%d-%H%M%S')))
    f = open(db_dump, 'wb')
    f.write(base64.decodestring(dump))
    f.close()
