#!/usr/bin/python
# -*- encoding: utf-8 -*-
import xmlrpclib
import sys
from os.path import dirname,join,isdir
from os import mkdir
import ConfigParser
import subprocess
import time

config = ConfigParser.RawConfigParser()
config.read(join(dirname(__file__),'update_modules.ini'))
host = config.get('Server', 'host')
port = config.get('Server', 'port')
backupdir = config.get('Server', 'backupdir')

if len(sys.argv) < 2:
    print "Usage: %s module1,module2,...."%(sys.argv[0],)
    sys.exit(1)

modules = sys.argv[1].split(',')
ok = True

def get_db(config):
    sections = config.sections()
    sections.pop(sections.index('Server'))
    ret = []
    for section in sections:
        user = config.get(section, 'user')
        dbname = config.get(section, 'dbname')
        pwd = config.get(section, 'password')
        ret.append((dbname, user, pwd))
    return ret

class Proxy():
    sock = False
    uid = False
    pwd = False
    dbname = False
    host = False
    port = False

    def __init__(self, host, port, dbname, username, password):
        self.dbname = dbname
        self.pwd = password
        self.host = host
        self.port = port
        sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/common'%(self.host,self.port))
        self.uid = sock.login(dbname, username, pwd)
        self.sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object'%(self.host,self.port))

    def exec_meth(self, module, method, *args):
        return self.sock.execute(self.dbname, self.uid, self.pwd, module, method, *args)

    def get_module_ids(self, modules):
        return self.exec_meth('ir.module.module', 'search', [('name', 'in', modules),('state','in',['installed', 'to upgrade'])])


for dbname, user, pwd in get_db(config):
    xml = Proxy(host, port, dbname, user, pwd)
    ids = xml.get_module_ids(modules)
    if len(ids) != len(modules):
        print "Base: %s, modules not present"%(dbname,)
        ok = False

if not ok:
    sys.exit(1)

if backupdir:
    for dbname, user, pwd in get_db(config):
        if not isdir(backupdir):
            mkdir(backupdir)

        args = ['/usr/bin/pg_dump', '-Fc', dbname, '-f', join(backupdir, '%s-%s.dump'%(dbname, time.strftime('%Y%m%d%H%M%S')))]
        subprocess.check_call(args)
else:
    inp = raw_input("There isn't any backups, are you sure ? (y/N) ")
    if inp not in ['Y','y']:
        sys.exit('Failed')


for dbname, user, pwd in get_db(config):
    xml = Proxy(host, port, dbname, user, pwd)
    ids = xml.get_module_ids(modules)
    xml.exec_meth('ir.module.module', 'button_upgrade', ids)
    xml.exec_meth('base.module.upgrade', 'upgrade_module', [])
