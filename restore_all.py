# -*- encoding: utf-8 -*-
import xmlrpclib
import os
import sys
import time
import base64
import re

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

if not os.path.exists(target_dir):
    print "Dir %s does not exist" % (target_dir, )
    sys.exit(0)
elif os.listdir(target_dir) == []:
    print "Dir %s is empty" % (target_dir, )
    sys.exit(0)

sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/db'%(host, port))
dbs_to_restore = []

for dump in os.listdir(target_dir):
    matches = re.search('^(.*)-[0-9]{8}-[0-9]{6}(?:-(.*))?.dump$', dump)
    if matches:
        db = matches.group(1)
        dbs_to_restore.append((dump, db))
    else:
        print "%s wrong format: nothing done"

if not dbs_to_restore:
    print "Nothing to restore"
    sys.exit(0)

ret = ''
while ret.lower() not in ('y', 'n'):
    print "Server %s, do you want to restore %s ? [y/n] " % (host, ' '.join([x[1] for x in dbs_to_restore]))
    ret = raw_input()
if ret.lower() == 'n':
    print "Abort"
    sys.exit(0)

for dump, db in dbs_to_restore:
    print "Restoring %s ..." % (db, )
    try:
        sock.restore(pwd, db, base64.encodestring(open(os.path.join(target_dir, dump)).read()))
    except Exception, e:
        print "Unable to restore %s: %s" % (db, e)
