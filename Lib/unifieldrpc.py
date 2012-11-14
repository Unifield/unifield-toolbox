# -*- encoding: utf-8 -*-
import xmlrpclib
import time

class Rpc():
    def __init__(self, dbname, user, pwd, host, port):
        self.dbname = dbname
        self.pwd = pwd
        sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/common' % (host, port))
        self.uid = sock.login(dbname, user, pwd)
        self.sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object'% (host, port))

    def exe(self, *a, **b):
        return self.sock.execute(self.dbname, self.uid, self.pwd, *a, **b)
