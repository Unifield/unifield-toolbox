# -*- encoding: utf-8 -*-
import os
import sys
import httplib2
import argparse
import ConfigParser
from subprocess import call
import re
from bzrlib.workingtree import WorkingTree
from bzrlib.branch import BzrBranch
import shutil
import psycopg2

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--host", "-H", metavar="host", default="last_sync_dump.dsp.uf3.unifield.org", help="Host [default: %(default)s]")
parser.add_argument("--force", "-f", action="store_true", default=False, help="Delete dump if exists")
parser.add_argument("--web-port", "-w", default=8061, help="Web port [default: %(default)s]")
parser.add_argument("--netrpc-port", "-n", default=8070, help="NetRPC port [default: %(default)s]")

parser.add_argument('directory', action='store', help='Directory to get the branch [default: current]')
parser.add_argument('version', action='store')
o = parser.parse_args()

cnx = httplib2.Http()
resp, content = cnx.request(os.path.join('http://%s' % o.host, o.version, 'info.txt'), "GET")

main_dir = os.path.realpath(o.directory)
if not os.path.exists(main_dir):
    os.makedirs(main_dir)

def get_branch_and_revno(path):
    if os.path.islink(path):
        path = os.path.realpath(path)
    wt = WorkingTree.open(path)
    lr = wt.last_revision()

    if isinstance(wt.branch, BzrBranch):
        parent = wt.branch.get_parent()
        if parent is None:
            parent = wt.branch.get_bound_location()
    else:
        parent = wt.branch.bzrdir.root_transport.base

    return parent, wt.branch.revision_id_to_dotted_revno(lr)[0]

def ask(qu):
    while True:
        print "%s [Y/n]" % qu
        ans = raw_input()
        if ans in ['Y','y', '']:
            return True
        if ans in ['n','N']:
            return False

def create_db(all_dbs):
    for dump in all_dbs:
        print "Restoring DB %s ..." % dump
        dump_file = os.path.join(dump_dir, '%s.dump'%dump)
        call(['dropdb', dump])
        call(['createdb', dump])
        call(['pg_restore', '--no-owner', '-d', dump, dump_file])


# Get the description file on the remote host
info_txt = os.path.join(main_dir, 'info.txt')
f = open(info_txt, 'w')
f.write("[Config]\n")
f.write(content)
f.close()
config = ConfigParser.RawConfigParser()
config.read(info_txt)


# Check or download the branches
for mod in ['unifield-addons', 'unifield-server', 'unifield-wm', 'sync_module_prod']:
    url = config.get('Config', '%s_url' % mod)
    revno = config.get('Config', '%s_revno' % mod)
    wk_dir = os.path.join(main_dir, mod)
    to_download = True
    if os.path.exists(wk_dir):
        local_branch, local_revno = get_branch_and_revno(wk_dir)
        to_download = False

        if local_branch != url or "%s"%local_revno != revno:
            print "%s, local: %s (%s), remote %s (%s)" % (mod, local_branch, local_revno, url, revno)
            if ask('Should I delete and re-branch the code ?'):
                    shutil.rmtree(wk_dir)
                    to_download = True

    if to_download:
        print 'bzr branch -r %s %s %s' % (revno, url, mod)
        call(['bzr', 'branch', '-r', revno, url, mod], cwd=main_dir)


dump_dir = os.path.join(main_dir, 'DBs')
if not os.path.exists(dump_dir):
    os.makedirs(dump_dir)

print "Get Dumps"
resp, content = cnx.request(os.path.join('http://%s' % o.host, o.version), "GET")
pattern = re.compile('="(\w+)\.dump"')
dumps = pattern.findall(content)
if not dumps:
    print "error: not dump found"
    sys.exit(1)

all_dbs = []
sync_db = False
for dump in dumps:
    new_name =  '%s_%s'%(o.version, dump)
    dump_file = os.path.join(dump_dir, '%s.dump'%new_name)
    all_dbs.append(new_name)
    if 'SYNC' in dump:
        sync_db = new_name
    if not os.path.exists(dump_file) or o.force:
        resp, content = cnx.request(os.path.join('http://%s' % o.host, o.version, "%s.dump"%dump), "GET")
        f = open(dump_file, 'wb')
        f.write(content)
        f.close
    else:
        print "Dump %s, already exists" % dump

print "Sync DB %s" % sync_db
print "I will drop and create the following DBs: %s" % ','.join(all_dbs)
if ask('Are you ok ?'):
    create_db(all_dbs)

print "Setting instance sync server"
for dump in all_dbs:
    if dump != sync_db:
        db = psycopg2.connect('dbname=%s'%dump)
        cr = db.cursor()
        cr.execute('update sync_client_sync_server_connection set database=%s, port=%s', (sync_db, o.netrpc_port))
        db.commit()
        cr.close()

addons_path = []
for ad in ['unifield-addons', 'unifield-wm', 'sync_module_prod', 'unifield-web']:
    addons_path.append(os.path.join(main_dir, ad))


print "Generate server config file"
openerprc = os.path.join(main_dir, 'openerprc')
config = ConfigParser.RawConfigParser()
if os.path.exists(openerprc):
    config.read(openerprc)
else:
    config.add_section('options')
config.set('options', 'netrpc_port', o.netrpc_port)
config.set('options', 'xmlrpcs', False)
config.set('options', 'xmlrpc', False)
config.set('options', 'root_path',  os.path.join(main_dir, 'unifield-server', 'bin'))
config.set('options', 'addons_path', ','.join(addons_path))
with open(openerprc, 'wb') as configfile:
    config.write(configfile)

print "Generate web config file"
config = ConfigParser.RawConfigParser()
web_config = os.path.join(main_dir, 'openerp-web.cfg')
if os.path.exists(web_config):
    config.read(web_config)
else:
    config.read(os.path.join(main_dir, 'unifield-web', 'doc' ,'openerp-web.cfg'))
config.set('global', 'server.socket_port', o.web_port)
config.set('global', 'openerp.server.port', o.netrpc_port)
with open(web_config, 'wb') as configfile:
    config.write(configfile)

print "To start the web:"
print "   cd %s" % (os.path.join(main_dir, 'unifield-web'))
print "   ./openerp-web.py -c ../openerp-web.cfg"
print ""
print "To start the server:"
print "   cd %s" % (os.path.join(main_dir, 'unifield-server', 'bin'))
print "   ./openerp-server.py -c ../../openerprc"


