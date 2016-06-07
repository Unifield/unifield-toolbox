#! /usr/bin/python

import xmlrpclib
import sys
import ConfigParser
import os
import time
import subprocess
RB = sys.argv[1]

def read_last_line(log_file):
    log_d = open(log_file, 'r')
    statinfo = os.stat(log_file)
    if statinfo.st_size > 2024:
        log_d.seek(-2024, os.SEEK_END)
    for l in log_d.readlines():
        print l.strip()
    log_d.close()

read_last_line('/home/%s/log/openerp-web-access.log' % RB)
print '----'
#read_last_line('/var/log/apache2/%s-access.log' % RB)
#print '----'
inp = raw_input("Restart ? [y/N]")
if inp not in ['Y','y']:
    sys.exit('Nothing done')

subprocess.check_call(['/etc/init.d/%s-server'%RB, 'restart'])
time.sleep(10)
rcfile = '/home/%s/etc/openerprc' % RB
p = ConfigParser.ConfigParser()
p.read([rcfile])
xmlrpc_port = dict(p.items('options'))['xmlrpc_port']

uid = 1
sock = xmlrpclib.ServerProxy('http://127.0.0.1:%s/xmlrpc/db'%(xmlrpc_port, ))
dbs = sock.list()
sock = xmlrpclib.ServerProxy('http://127.0.0.1:%s/xmlrpc/object'%(xmlrpc_port, ))
for db in dbs:
    if 'RW' not in db and 'SYNC' not in db and db != 'se_testup':
        print 'Reconnect %s' % db
        try:
            login = sock.execute(db, uid, 'admin', 'sync.client.sync_server_connection', 'read', 1, ['login'])['login']
            sock.execute(db, uid, 'admin', 'sync.client.sync_server_connection', 'write', [1], {'password': login})
            sock.execute(db, uid, 'admin', 'sync.client.sync_server_connection', 'action_connect', [1])
        except Exception, e:
            print "%s error %s" % (db ,e)

read_last_line('/home/%s/log/openerp-server.log' % RB)

