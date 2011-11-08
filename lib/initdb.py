#!/usr/bin/python
# -*- encoding: utf-8 -*-


import optparse
import os
import getpass
import sys
import glob
import re
import base64
import time
import utils
import socket

def nb_request():
    return len(utils.rpc.RPCProxy('res.request').search([('act_to', 'in', [utils.rpc.session.uid])]))

def import_csv(lpath):
    for f in sorted(glob.glob(os.path.join(lpath, '*.csv'))): 
        nbr = nb_request()
        m = re.match('.*/\d+_(.*)\.csv', f)
        if not m:
            continue
        obj = m.group(1)
        
        fo = open(f)
        wid = utils.rpc.RPCProxy('import_data').create({'ignore': 1, 'object': obj, 'file': base64.encodestring(fo.read()), 'debug': True})
        fo.close()
        utils.rpc.RPCProxy('import_data').import_csv([wid])
        while nb_request() == nbr:
            time.sleep(5)

def wizard_init():
    wiz = utils.rpc.RPCProxy('res.config').start([])
    while wiz and wiz.get('res_model') not in ('base.setup.config','ir.ui.menu'):
        id = utils.rpc.RPCProxy(wiz['res_model']).create({})
        wiz = utils.rpc.RPCProxy(wiz['res_model']).action_next([id])
    if wiz.get('res_model') == 'base.setup.config':
        utils.rpc.RPCProxy(wiz['res_model']).config([])
        return True
    return False

def try_socket(sock, host, port, max_wait, start_time=False, pidfile=False):
    if not start_time:
        start_time = time.time()
    if pidfile:
        if os.path.isfile(pidfile):
            return try_socket(sock, host, port, max_wait)
        else:
            if time.time()-start_time > max_wait:
                return False
            time.sleep(5)
            return try_socket(sock, host, port, max_wait, start_time, pidfile)
    try:
        sock.connect((host, int(port)))
    except socket.error, e:
        if e.errno == 111:
            if time.time()-start_time > max_wait:
                return False
        time.sleep(5)
        return try_socket(sock, host, port, max_wait, start_time)
    sock.close()
    return True

def connect_db(user, pwd, dbname, host, port, path, pidfile=False):
    msg = []
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if try_socket(sock, host, port, 450, pidfile=pidfile):
        utils.rpc.initialize(host, port, 'socket', storage=dict())
        utils.rpc.session.login(dbname, user, pwd)
        wiz = wizard_init()
        if wiz:
            import_csv(path)
            return 'Data successfully loaded'
        return 'Data not loaded: no init wizard to execute' 
    
    raise Exception('Data not loaded: server is not ready')


if __name__=="__main__":
    usage = "usage: %prog [options] import_dir"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-d", "--database", dest="dbname", help="Database [default: %default]",default="test")
    parser.add_option("-H", "--host", dest="host", help="Host [default: %default]",default="127.0.0.1")
    parser.add_option("-p", "--port", dest="port", help=u"Port [default: %default]",default="8070")
    parser.add_option("-u", "--user", dest="user", help="User [default: %default]", default="admin")
    parser.add_option("-w", "--password", dest="pwd", help="Password")
    (opt, args) = parser.parse_args()

    if len(args) < 1:
        parser.error("Missing arg import_dir")

    if not opt.pwd:
        opt.pwd = getpass.getpass('Password : ')

    connect_db(opt.user, opt.pwd, opt.dbname, opt.host, opt.port, args[0])
