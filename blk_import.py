#!/usr/bin/python
# -*- encoding: utf-8 -*-


import xmlrpclib
import optparse
import os
import getpass
import sys
import glob
import socket
import re
import base64
import time

usage = "usage: %prog [options] import_dir"
parser = optparse.OptionParser(usage=usage)
parser.add_option("-d", "--database", dest="dbname", help="Database [default: %default]",default="test")
parser.add_option("-H", "--host", dest="host", help="Host [default: %default]",default="127.0.0.1")
parser.add_option("-p", "--port", dest="port", help=u"Port [default: %default]",default="8069")
parser.add_option("-u", "--user", dest="user", help="User [default: %default]", default="admin")
parser.add_option("-w", "--password", dest="pwd", help="Password")
(opt, args) = parser.parse_args()

if len(args) < 1:
    parser.error("Missing arg import_dir")

if not opt.pwd:
    opt.pwd = getpass.getpass('Password : ')

try:
    sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/common'%(opt.host,opt.port))
    uid = sock.login(opt.dbname, opt.user, opt.pwd)
    sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object'%(opt.host,opt.port))
except socket.error, err:
    sys.exit(str(err))
except xmlrpclib.Fault:
    sys.exit('Error database name')

if not uid:
    sys.exit('User or password incorrect')

def nb_request():
    return len(sock.execute(opt.dbname, uid, opt.pwd, 'res.request', 'search', [('act_to', 'in', [uid])]))

for f in sorted(glob.glob(os.path.join(args[0], '*.csv'))): 
    nbr = nb_request()
    m = re.match('.*/\d+_(.*)\.csv', f)
    if not m:
        print >> sys.stderr, "File %s not ignored"%(f, )
        continue
    obj = m.group(1)
    
    print >> sys.stderr, obj
    fo = open(f)
    wid = sock.execute(opt.dbname, uid, opt.pwd, 'import_data', 'create', {'ignore': 1, 'object': obj, 'file': base64.encodestring(fo.read()), 'debug': True})
    fo.close()
    sock.execute(opt.dbname, uid, opt.pwd, 'import_data', 'import_csv', [wid])
    while nb_request() == nbr:
        time.sleep(5)
