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

defaults = {
    'host': 'last_sync_dump.dsp.uf3.unifield.org',
    'web_port': 8061,
    'netrpc_port': 8070,
    'directory': os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')),
    'force': False,
}
cfile = os.path.realpath(os.path.expanduser('~/.mkdbrc'))
if os.path.exists(cfile):
    config = ConfigParser.SafeConfigParser()
    config.read([cfile])
    defaults.update(dict(config.items("Defaults")))


parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.set_defaults(**defaults)
parser.add_argument("--host", "-H", metavar="host")
parser.add_argument("--force", "-f", action="store_true", help="Delete dump if exists")
parser.add_argument("--web-port", "-w", help="Web port")
parser.add_argument("--netrpc-port", "-n",  help="NetRPC port")
parser.add_argument("--syncdb", "-s", action="store_true",  help="For existing db: update sync host/port (the others are always updated)")
parser.add_argument("--dropdb-bydefault", action="store_true",  help="Default choice for droping db question")

parser.add_argument('--directory', action='store', help='Directory to get the branch [default: current]')
parser.add_argument('--version', action='store')
o = parser.parse_args()
cnx = httplib2.Http()
if not o.version:
    # Get the last env
    url = os.path.join('http://%s' % o.host)
    resp, content = cnx.request(url, "GET")
    pattern = re.compile('href="([0-9]{12})/"')
    match = pattern.search(content)
    if match:
        o.version = match.group(1)
        print "Get last sync env: %(ver)s in %(dir)s/%(ver)s" % {'ver': o.version, 'dir':o.directory}
    else:
        raise Exception('No version found ! check %s' % url)

resp, content = cnx.request(os.path.join('http://%s' % o.host, o.version, 'info.txt'), "GET")

main_dir = os.path.realpath(os.path.join(o.directory, o.version))
if not os.path.exists(main_dir):
    os.makedirs(main_dir)


def test_db_exists(dbname):
    try:
        psycopg2.connect("dbname=%s"%dbname)
        return True
    except psycopg2.OperationalError:
        return False

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

def ask(qu, default_choice):
    while True:
        choice = "[y/N]"
        if default_choice:
            choice = "[Y/n]"

        print "%s %s" % (qu, choice),
        ans = raw_input()
        if ans in ['Y','y'] or default_choice and not ans:
            return True
        if ans in ['n','N'] or not default_choice and not ans:
            return False

def create_db(all_dbs):
    for dump in all_dbs:
        print "Restoring DB %s ..." % dump
        dump_file = os.path.join(dump_dir, '%s.dump'%dump)
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
for mod in ['unifield-addons', 'unifield-server', 'unifield-wm', 'sync_module_prod', 'unifield-web']:
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

print "Get db dumps ..."
url = os.path.join('http://%s' % o.host, o.version)
resp, content = cnx.request(url, "GET")
pattern = re.compile('="(\w+)\.dump"')
dumps = pattern.findall(content)
if not dumps:
    print "Error: not dump found, check: %s" % url
    sys.exit(1)

all_dbs = []
sync_db = False
existing_dump = []
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
        existing_dump.append(dump)

if existing_dump:
    print "Dumps %s,\n\t already exist, use -f option to force the download." % ','.join(existing_dump)

if not sync_db:
    print "Error: no dbname detected for the sync server"
    sys.exit(1)

db_exists = []
for db in all_dbs:
    if test_db_exists(db):
        db_exists.append(db)


if db_exists:
    if ask("I'll drop these dbs: %s\nAre you ok to drop them ?" % ','.join(db_exists), default_choice=o.dropdb_bydefault):
        print "Dropping could fail if the server is running"
        for dump in db_exists:
            call(['dropdb', dump])
    else:
        print "I'll not touch these dbs (except if we are using --syncdb)"
        all_dbs = list(set(all_dbs) - set(db_exists))

create_db(all_dbs)

print "Setting instance sync server ..."
db_to_update = all_dbs[:]
if o.syncdb:
    db_to_update += db_exists

for dump in db_to_update:
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
print "... http://127.1.2.3:%s " % o.web_port
