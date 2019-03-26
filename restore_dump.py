#!/usr/bin/env python
# -*- encoding: utf-8 -*-

examples = """
Restore dumps from: Jira, UniField Web server, local directoy or a daily light sync

You can store defaults values in the file ~/.restore_dumprc, section [Restore].

Examples:
  Restore dumps attached to jira issue us-1331:
   %(prog)s -j us-1331 --j-user jfb

  Restore dumps from a local directory:
   %(prog)s -d my/local/dir

  List dbs on ct1:
   %(prog)s -f -l

  Restore 2 dumps from ct1:
   %(prog)s -f --include LB1_COO,LB1_EEH

  Restore LB1 dumps from ct4, a daily light sync server and start a sync
   %(prog)s -f ct4 --include LB1 -s --apache-user XXX --apache-password ZZZ --sync-run

  Restore se_HQ1 and se_SYNC_SERVER from se.dsp.uf3.unifield.org:
   %(prog)s -f se.dsp.uf3.unifield.org --include se_HQ1+,SYNC

  Restore a daily light sync server
   %(prog)s --sync-only

Please note:
 - stock mission ir.cron is disabled by this script

"""
import os
import sys
import argparse
import getpass
import httplib2
from HTMLParser import HTMLParser
import urllib
import re
import psycopg2
import tempfile
from subprocess import call
#import threading
import time
from base64 import b64encode
from urlparse import urlparse
import zipfile

webdav = True
try:
    import easywebdav
except ImportError:
    print sys.stderr.write("Run pip install easywebdav to restore dumps from OwnCloud")
    webdav = False


try:
    from requests.packages import urllib3
    # disable tls warning with jira
    urllib3.disable_warnings()
    import jira
except ImportError, AttributeError:
    raise SystemExit("Please install jira lib:\n sudo pip install jira")


has_oerplib = True
try:
    import oerplib
except ImportError:
    has_oerplib = False
    pass
import hashlib
import shutil
import ConfigParser

class dbmatch(object):
    include_dbs = []

    def match(self, name):
        if not self.include_dbs:
            return True
        for x in self.include_dbs:
            if x.endswith('+'):
                if x[0:-1] == name:
                    return True
            elif re.search(x, name):
                return True

class PG_param(object):
    user = False
    password = False
    host = False
    port = False

    @classmethod
    def set(self, user=False, password=False, host=False, port=False):
        self.user = user
        self.password = password
        self.host = host
        self.port = port

    @classmethod
    def get_dsn(self, dbname):
        ret = {'dbname': dbname}
        for x in ['user', 'password', 'host', 'port']:
            if getattr(self, x):
                ret[x] = getattr(self, x)
        return ' '.join(['%s=%s' % (x, ret[x]) for x in ret])


class MyHTMLParser(HTMLParser, dbmatch):
    dbs = []
    version = False
    div_footer = False
    div_version = False

    def __init__(self, include_dbs):
        super(MyHTMLParser, self).__init__()
        self.include_dbs = include_dbs.split(',')

    def handle_starttag(self, tag, attrs):
        if tag == 'option':
            attrs_dic = dict(attrs)
            if attrs_dic.get('value'):
                db_name = attrs_dic['value']
                if self.match(db_name):
                    self.dbs.append(db_name)
        if tag == 'div' and dict(attrs).get('class') == 'footer_a':
            self.div_footer = True
        if self.div_footer and tag == 'div' and dict(attrs).get('align') == 'center':
            self.div_version = True
            self.div_footer = False

    def handle_data(self, data):
        if self.div_version:
            v = data.strip().replace('UniField ', '')
            self.version = re.sub('-[0-9]{8}-[0-9]{6}$', '', v)
            self.div_version = False

class Directory(dbmatch):
    def __init__(self, directory, include_dbs):
        self.directory = directory
        self.dumps = []
        self.info = 'Directory %s'%directory
        self.include_dbs = include_dbs.split(',')
        for listfile in os.listdir(directory):
            full_file = os.path.join(directory, listfile)
            if os.path.isfile(full_file):
                name, ext = os.path.splitext(listfile)
                if (not ext or ext == '.dump') and self.match(name):
                    if 'SYNC' in name:
                        self.dumps.insert(0, full_file)
                    else:
                        self.dumps.append(full_file)

    def get_dbs(self):
        return self.dumps

    def get_db_name(self, db):
        return os.path.splitext(os.path.basename(db))[0]

    def write_dump(self, db, file_desc):
        src = open(db, 'rb')
        shutil.copyfileobj(src, file_desc)
        src.close()


class RBIndex(dbmatch):
    include_dbs = []
    dbs = []
    info = ''

    def __init__(self, rb_name, include_dbs = ''):
        if rb_name == 'se':
            rb_name = 'se_dump.dsp.uf3.unifield.org'
        split_name = rb_name.split('.')
        if len(split_name) == 1:
            rb_name = '%s.uf5.unifield.org' % rb_name
            split_name = rb_name.split('.')

        if not split_name[0].endswith('_dump'):
            split_name[0] = "%s_dump" % split_name[0]
            rb_name = '.'.join(split_name)
        if not rb_name.startswith('http'):
            rb_name = 'http://%s' % rb_name

        self.rb_name = rb_name
        self.include_dbs = include_dbs.split(',')
        cnx = httplib2.Http()
        resp, content = cnx.request(rb_name, "GET")
        pattern = re.compile('href="([0-9]{12})/"')
        match = pattern.search(content)
        empty_date = '000000000000'
        max_date = empty_date
        if match:
            version = match.group(1)
            if version > max_date:
                max_date = version
        self.info = '%s %s' % (rb_name, max_date)
        if max_date != empty_date:
            url = os.path.join(rb_name, max_date)
            resp, content = cnx.request(url, "GET")
            pattern = re.compile('="([^"]+)\.dump"')
            for dump in pattern.findall(content):
                if self.match(dump):
                    full_dump = '%s/%s.dump' % (max_date, dump)
                    if 'SYNC' in dump:
                        self.dbs.insert(0, full_dump)
                    else:
                        self.dbs.append(full_dump)

    def get_dbs(self):
        return self.dbs

    def get_db_name(self, db):
        return db.split('/')[-1]

    def write_dump(self, db, file_desc):
        f = urllib.urlopen('%s/%s' % (self.rb_name, db))
        while True:
            data = f.read(10*1024)
            if data == '':
                break
            file_desc.write(data)
        f.close()


class ApacheIndexes(object):
    host = 'sync-prod_dump.rb.unifield.org'
    proto = 'http'
    dump_name = 'SYNC_SERVER_LIGHT'

    def __init__(self, user=False, password=False, dump_name=False):
        self.user = user
        self.password = password
        if dump_name:
            self.dump_name = dump_name

    def get_dbs(self):
        return [self.dump_name]

    def get_db_name(self, db):
        return db

    def write_dump(self, db, file_desc):
        auth_str = ''
        if self.user and self.password:
            auth_str = '%s:%s@' % (self.user, self.password)
        f = urllib.urlopen("%s://%s%s/%s" % (self.proto, auth_str, self.host, db))
        while True:
            data = f.read(10*1024)
            if data == '':
                break
            file_desc.write(data)
        f.close()

class Owncloud(dbmatch):
    def __init__(self, url, passwd, include_dbs):
        self.dumps = []
        self.info = 'OwnCloud %s' % url
        parsed_url = urlparse(url)
        self.dav = easywebdav.connect(parsed_url.netloc,
                                      username=parsed_url.path.split('/')[-1],
                                      password=passwd,
                                      protocol=parsed_url.scheme)

        self.owc_path = '/owncloud/public.php/webdav/'

        self.include_dbs = include_dbs.split(',')
        for listfile in self.dav.ls(self.owc_path):
            full_file = listfile.name
            name, ext = os.path.splitext(full_file.split('/')[-1])
            if name and (not ext or ext in ('.dump','.zip')) and self.match(name):
                if 'SYNC' in name:
                    self.dumps.insert(0, full_file)
                else:
                    self.dumps.append(full_file)
            elif full_file == self.owc_path:
                # single file shared
                self.dumps.append(full_file)

    def get_dbs(self):
        return self.dumps

    def get_db_name(self, db):
        if db == self.owc_path:
            return 'No_Name'
        return '-'.join(os.path.splitext(os.path.basename(db))[0].split('-')[0:2])

    def write_dump(self, db, file_desc):
        temp1 = tempfile.NamedTemporaryFile(delete=True)
        self.dav.download(db, temp1)
        temp1.seek(0, 0)
        name = None
        if zipfile.is_zipfile(temp1.name):
            zip_f = zipfile.ZipFile(temp1.name)
            zip_names = zip_f.namelist()
            name = '-'.join(zip_names[0].split('-')[0:2])
            temp2 = zip_f.open(zip_names[0])
            temp1.close()
            temp1 = temp2
        shutil.copyfileobj(temp1, file_desc)
        temp1.close()
        return name


class Postgres(dbmatch):
    host = 'uf7.unifield.org'
    port = '5432'

    def __init__(self, host, cert, key, include_dbs):
        self.dbs = []
        self.cert = cert
        self.key = key
        self.host = host
        self.include_dbs = include_dbs.split(',')
        conn = psycopg2.connect(host=self.host, port=self.port, sslmode='require', sslcert=cert, sslkey=key, user='production-dbs', dbname='template1')
        cr = conn.cursor()
        cr.execute('SELECT datname FROM pg_database WHERE pg_get_userbyid(datdba) = current_user')
        for x in  cr.fetchall():
            if self.match(x[0]):
                self.dbs.append(x[0])
        self.info = 'Postgres %s:%s' % (self.host, self.port)
        conn.close()

    def get_dbs(self):
        return self.dbs

    def get_db_name(self, db):
        return db

    def write_dump(self, db, file_desc):
        my_env = os.environ.copy()
        my_env['PGSSLCERT'] = self.cert
        my_env['PGSSLKEY'] = self.key
        call(['pg_dump', '-Fc', db, '--host', self.host, '--port', self.port, '--user', 'production-dbs'], stdout=file_desc, env=my_env)


class Web(object):

    default_host = 'unifield-%s.ocg.msf.org:8061'
    default_password = 'bkAdmin'
    default_rb_password = '4unifield'

    def __init__(self, host, password, include_dbs, basic_user=False, basic_password=False):
        if host:
            if len(host) == 3:
                host = self.default_host % host
            elif host == 'prod-dbs':
                host = 'https://production-dbs.uf7.unifield.org'
        else:
            host = self.default_host % 'ct1'

        #  httplib2 does not follow redirect
        if host == 'se.dsp.uf3.unifield.org':
            host = 'se.perf.unifield.biz'

        if not password and (host.endswith('unifield.org') or host.endswith('unifield.biz')):
            password = self.default_rb_password

        if host.startswith('http'):
            url = '%s/' % (host, )
        else:
            url = 'http://%s/' % (host,)
        self.password = password or self.default_password
        self.backup_url = '%sopenerp/database/do_backup' % (url, )
        self.headers = {
            'Referer': '%sopenerp/database/backup' % (url, ),
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        if basic_user and basic_password:
            self.headers['Authorization'] = 'Basic %s' %  b64encode(b"%s:%s" % (basic_user, basic_password)).decode("ascii")


        cnx = httplib2.Http(disable_ssl_certificate_validation=True)
        resp, content = cnx.request('%sopenerp/database/backup' % (url, ) , "GET", headers=self.headers)
        parser = MyHTMLParser(include_dbs)
        parser.feed(content)
        parser.close()
        self.dbs = parser.dbs
        self.info = '%s %s' % (url, parser.version)

    def get_dbs(self):
        dbs = []
        for db in self.dbs:
            if 'SYNC' in db:
                dbs.insert(0, db)
            else:
                dbs.append(db)
        return dbs

    def get_db_name(self, db):
        return db

    def write_dump(self, db, file_desc):
        cnx = httplib2.Http(disable_ssl_certificate_validation=True)
        resp, content = cnx.request(self.backup_url, 'POST', body=urllib.urlencode({'dbname': db, 'password': self.password}), headers=self.headers)
        file_desc.write(content)

class JiraZipAttachment():
    def __init__(self, options, name, j_obj):
        self.path = j_obj._get_url('attachmentzip/unzip/%s/%s[%s]/' % tuple(options), base='{server}/secure/{path}')
        self.j_obj = j_obj
        self.filename = name

    def get(self):
        return self.j_obj._session.get(self.path).content

class JIRA(dbmatch):
    host = 'http://jira.unifield.org'
    def __init__(self, host, user, password, issue_key, include_dbs):
        if host:
            self.host = host
        try:
            j_obj = jira.JIRA(self.host, options={'check_update': False}, basic_auth=(user, password))
            self.issue = j_obj.issue(issue_key)
        except jira.exceptions.JIRAError, error:
            if error.status_code == 401:
                message = 'Unauthorized'
            else:
                message = error.text
            sys.stderr.write("Jira Error %s: %s\n" % (error.status_code, message))
            sys.exit(1)
        self.info = 'Jira key %s' % issue_key
        self.include_dbs = include_dbs.split(',')
        self.attach = []
        for att in self.issue.fields.attachment:
            if att.filename.endswith('zip'):
                zip_content = j_obj._get_json('attachment/%(id)s/expand/raw' % {'id': att.id})
                if zip_content and zip_content.get('entries'):
                    for entry in zip_content['entries']:
                        if entry['name'].endswith('.dump') and self.match(entry['name']):
                            self.attach.append(JiraZipAttachment([self.issue.id, att.id, entry['entryIndex']], entry['name'], j_obj))
            if att.filename.endswith('.dump') and self.match(att.filename):
                self.attach.append(att)

    def get_dbs(self):
        dbs = []
        for att in self.attach:
            if 'SYNC' in att.filename:
                dbs.insert(0, att)
            else:
                dbs.append(att)
        return dbs

    def get_db_name(self, attach):
        return attach.filename

    def write_dump(self, attach, file_desc):
        #for content in attach.iter_content():
        #    file_desc.write(content)
        file_desc.write(attach.get())

def get_harware_id():
    mac = []
    for line in os.popen("/sbin/ifconfig"):
        if line.find('Ether') > -1:
            mac.append(line.split()[4])
    mac.sort()
    return hashlib.md5(''.join(mac)).hexdigest()

def do_upgrade(port, database, uf_pass):
    sys.stdout.write("upgrade base module\n")
    # Max 1h to upgrade
    max_sec = 60*60
    begin = time.time()
    while True:
        try:
            xmlrpc = oerplib.OERP('127.0.0.1', protocol='xmlrpc', port=port, database=database, version='6.0')
            xmlrpc.login('admin', uf_pass)
            return True
            #sys.exit(0)
        except oerplib.error.RPCError, e:
            if 'ServerUpdate' in '%s'%e.message or ( e.args and isinstance(e.args, tuple) and 'ServerUpdate' in e.args[0]):
                if time.time() - begin > max_sec:
                    sys.stderr.write("%s: timeout during upgrade" % (database,))
                    return True
                time.sleep(10)
            else:
                sys.stderr.write("%s: unable to upgrade modules\n%s\n" % (database, e))
                return True
                #sys.exit(0)
    return True
    #sys.exit(0)

def connect_and_sync(dbs_name, sync_port, sync_run, sync_db=False, uf_pass='admin'):
    if not has_oerplib:
        return False
    if not isinstance(dbs_name, (list, tuple)):
        dbs_name = [dbs_name]
    for db in dbs_name:
        if 'SYNC' in db:
            if not sync_db:
                sync_db = db
            continue
        if sync_db:
            try:
                xmlrpc = oerplib.OERP('127.0.0.1', protocol='xmlrpc', port=sync_port, database=db, version='6.0')
                sys.stdout.write("%s: Connect to sync\n" % (db, ))
                xmlrpc.login('admin', uf_pass)
                conn_manager = xmlrpc.get('sync.client.sync_server_connection')
                conn_ids = conn_manager.search([])
                conn_manager.write(conn_ids, {'automatic_patching': False, 'password': uf_pass})
                conn_manager.connect()
                if o.sync_run:
                    xmlrpc.get('sync.client.entity').sync_manual_threaded()
                    sys.stdout.write("Start sync\n")
            except Exception, e:
                sys.stderr.write("%s: unable to sync connect\n%s\n" % (db, e))
    return True

def restore_dump(transport, prefix_db, output_dir=False, sql_queries=False, sync_db=False, sync_port=0 , drop=False, upgrade=False, passw=False, removeprefix=False):
    restored = []
    sql_data = {
        'hardware_id': get_harware_id(),
        'xmlrpc_port': sync_port or 8069,
        'server_db': sync_db or 'SYNC_SERVER',
    }
    list_threads = []
    for db in transport.get_dbs():
        dump_name = transport.get_db_name(db)
        if output_dir:
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            file_name = os.path.join(output_dir, dump_name)
            f = open(file_name, 'wb')
        else:
            f = tempfile.NamedTemporaryFile(mode='wb', delete=False)
            file_name = f.name
        sys.stdout.write("get %s to %s\n" % (dump_name, file_name))
        ex_dump = transport.write_dump(db, f)
        if ex_dump:
            dump_name = ex_dump
        f.close()

        if not os.path.getsize(file_name):
            sys.stderr.write("Warning:%s dump %s is empty !\n" % (dump_name, file_name))
            continue

        new_db_name = dump_name
        if removeprefix:
            new_db_name = re.sub('^'+removeprefix, '', new_db_name)
        if prefix_db:
            new_db_name = '%s_%s' % (prefix_db, new_db_name)
        new_db_name = re.sub('-[0-9]{6}(-(A|B|BP))?-UF.*.dump$', '', new_db_name).replace(' ','_')
        new_db_name = re.sub('.dump$', '', new_db_name)
        orig_db_name = new_db_name
        ok = False
        i = 1
        # check if db exists
        cant_drop = False
        while not ok:
            try:
                db_conn = psycopg2.connect(PG_param.get_dsn(new_db_name))
                if drop and not cant_drop:
                    db_conn.close()
                    if call(['dropdb', new_db_name]) != 0:
                        cant_drop = True
                        sys.stdout.write("Unable to drop %s\n" % new_db_name)
                    else:
                        break
                new_db_name = '%s_%s' % (orig_db_name, i)
                db_conn.close()
                i += 1
            except:
                ok = True
        sys.stdout.write("restore %s\n" % new_db_name)
        call(['createdb', new_db_name])
        call(['pg_restore', '--no-owner', '--no-acl', '-n', 'public', '-d', new_db_name, file_name])
        restored.append(new_db_name)
        sys.stdout.write("restored\n")
        if not output_dir:
            os.remove(file_name)

        attach_patch = os.path.expanduser('~/Unifield/attachments/%s' % (new_db_name))
        if not os.path.isdir(attach_patch):
            os.makedirs(attach_patch)
        sql_data['attach_patch'] = attach_patch

        is_server_db = 'SYNC' in new_db_name
        query_for_server = None
        db_conn = psycopg2.connect(PG_param.get_dsn(new_db_name))
        cr = db_conn.cursor()
        if sql_queries:
            sys.stdout.write("execute sql queries\n")
            if is_server_db:
                if not sync_db:
                    sql_data['server_db'] = new_db_name
            for query in sql_queries.split("\n"):
                if query:
                    if query.startswith('-- INSTANCE'):
                        query_for_server = False
                        continue
                    elif query.startswith('-- SERVER'):
                        query_for_server = True
                        continue
                    elif query.startswith('-- BOTH'):
                        query_for_server = None
                        continue
                    if query_for_server is None or query_for_server == is_server_db:
                        try:
                            cr.execute(query, sql_data)
                            db_conn.commit()
                        except psycopg2.ProgrammingError, e:
                            sys.stderr.write("Error during sql queries:\n%s\n" % e)
                            db_conn.rollback()
                            cr = db_conn.cursor()

            # increment sequences so db ids used after the dump are not re-used
            cr.execute("SELECT c.relname FROM pg_class c WHERE c.relkind = 'S'")
            for x in cr.fetchall():
                cr.execute("SELECT last_value FROM %s" % x[0])
                new_seq = cr.fetchone()[0]*2
                cr.execute("ALTER SEQUENCE %s RESTART WITH %s" % (x[0], new_seq))
            cr.execute("update ir_sequence set number_next=number_next*2")
            db_conn.commit()

            if is_server_db and upgrade:
                # if prod sync server: install msf_sync_data_server to auto update sync rules
                # change xmlid of existing sync_server.message_rule / sync.server.group_type
                cr.execute("select state from ir_module_module where name='msf_sync_data_server'")
                x = cr.fetchone()
                if x and x[0] == 'uninstalled':
                    cr.execute("update ir_module_module set state='to upgrade' where name='msf_sync_data_server'")
                    cr.execute("update ir_model_data set module='msf_sync_data_server' where model='sync_server.message_rule' and module=''")
                    for xmlid, group_name in [
                            ('group_type_oc', 'OC'),
                            ('group_type_usb', 'USB'),
                            ('group_type_misson', 'MISSION'),
                            ('group_type_coordo', 'COORDINATIONS'),
                            ('group_type_hq_mission', 'HQ + MISSION'),
                    ]:
                        cr.execute('select id from sync_server_group_type where name=%s', (group_name, ))
                        res_id = cr.fetchone()[0]

                        cr.execute("""insert into ir_model_data (name, module, model, res_id, noupdate, force_recreation)
                            values (%s, 'msf_sync_data_server', 'sync.server.group_type', %s, 'f', 'f') """, (xmlid, res_id))
                    db_conn.commit()


        if upgrade:
            do_upgrade(sync_port, new_db_name, passw)
            #thread = threading.Thread(target=do_upgrade, args=(sync_port, new_db_name, passw))
            #list_threads.append(thread)
            #thread.start()
        #call(['vacuumdb', '-Z', new_db_name])
        cr.execute('ANALYZE')
        db_conn.close()
    return restored, list_threads

if __name__ == "__main__":
    defaults = {
        'j_host': 'http://jira.unifield.org',
        'sync_port': '8070',
        'prefix': getpass.getuser(),
        'uf_password': 'admin',
        'upgrade': False,
    }
    rcfile = '~/.restore_dumprc'
    cfile = os.path.realpath(os.path.expanduser(rcfile))
    if os.path.exists(cfile):
        config = ConfigParser.SafeConfigParser()
        config.read([cfile])
        defaults.update(dict(config.items("Restore")))
    if not defaults.get('use_xmlrpc'):
        # compat: sync_port is the netrpc port
        netrpc = int(defaults['sync_port'])
        if netrpc >= 10000:
            # RB
            defaults['sync_port'] = netrpc + 2
        else:
            defaults['sync_port'] = netrpc - 1
    parser = argparse.ArgumentParser()
    parser.set_defaults(**defaults)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--examples', action='store_true', help='show usage examples and exit')
    group.add_argument('-j', '--issue', action='store', help='restore from Jira Issue Key')
    group.add_argument('-d', '--from-dir', action='store', help='restore dump from directory')
    group.add_argument('-p', '--postgres', action='store', help='restore dump from posgtres')
    group.add_argument('-f', '--uf-web', metavar='HOST[:PORT]', nargs='?', default=' ', help="UniField Web host:port default: ct1")
    if webdav:
        group.add_argument('-c', '--oc',  help="OwnCloud url")
    group.add_argument('--rb', metavar='HOST[:PORT]', help="From mkdb rb_dump exports")
    group.add_argument('--sync-only', action='store_true', help='restore *only* light sync')

    parser.add_argument("--include", "-i", metavar="DB1,DB2", default='', help="comma separated list of dbs to restore (postfix db_name with + for exact match)")
    parser.add_argument("--uf-password", action='store', help="UniField admin login & password")
    parser.add_argument("--drop", action='store_true', help="drop db if exists")
    parser.add_argument("--upgrade", action='store_true', help="upgrade base module")
    parser.add_argument('-o', '--directory', action='store', default='', help='save dumps to directory')
    parser.add_argument('--sql', nargs='?', default='True',  action='store', help='sql file to execute, set empty to disable default sql execution')

    parser.add_argument('-l', '--list', action='store_true', help='list dumps and exit')
    parser.add_argument('--prefix', nargs='?', metavar="DB PREFIX", help="prefix dbname by a string (set empty to disable) [default: user]")
    parser.add_argument('--remove-prefix', default='', metavar="DB PREFIX TO REMOVE", help="remove prefix from orignal dbname")
    parser.add_argument('--sync-port', help='sync xmlrpc port, used to update instances [default: %(default)s]')
    parser.add_argument('--sync-db', help='sync server db, used to update instances [default: %(default)s]')
    parser.add_argument('--sync-run', action="store_true", help='try to start sync')
    parser.add_argument('--db-port', action="store", help='PSQL port')
    parser.add_argument('--db-user', action="store", help='PSQL user')
    parser.add_argument('--db-password', action="store", help='PSQL Password')
    parser.add_argument('--db-host', action="store", help='PSQL Host')
    parser.add_argument('--apache-prod-user', action="store", help='Apache User')
    parser.add_argument('--apache-prod-password', action="store", help='Apache Password')

    parser.add_argument('--trust-me-i-know-what-i-m-doing', action="store_true", help=argparse.SUPPRESS),
    parser.add_argument('--auto-confirm', action="store_true", help=argparse.SUPPRESS),
    sync_light = parser.add_argument_group('Restore Sync Light')
    sync_light.add_argument('-s', '--sync', action='store_true', help='restore light sync from uf5 daily sync-prod')
    sync_light.add_argument('--apache-user', metavar="USER")
    sync_light.add_argument('--apache-password', metavar="PASSWORD")

    jira_parser = parser.add_argument_group('Restore from Jira')
    jira_parser.add_argument("--j-host", metavar='JIRA_HOST')
    jira_parser.add_argument("-u", "--j-user", metavar="JIRA_USER")

    web_parser = parser.add_argument_group('Restore from UniField Web')
    web_parser.add_argument("--web-pass", "-w", metavar="pwd", default="", help="web backup password")

    web_parser = parser.add_argument_group('Restore from OwnCloud')
    web_parser.add_argument("--oc-pass", metavar="ocpwd", default="", help="OwnCloud Pass")

    sync_parser = parser.add_argument_group('Restore Sync Server Light')
    sync_parser.add_argument("--server-type", "-t", choices=['no_master', 'with_master', 'no_update', '7days'], default='no_update', help="kind of sync server dump to restore: no_master: only the last 2 months upd/msg, with_master: last 2 months upd/msg + master updates, no_update: empty sync server without any upd/msg, [default: %(default)s]")

    psql_parser = parser.add_argument_group('Restore From PSQL')
    psql_parser.add_argument("--postgres-cer", action="store", help="PSQL certificate")
    psql_parser.add_argument("--postgres-key", action="store", help="PSQL key")

    o = parser.parse_args()
    if o.examples:
        sys.stdout.write(examples % {'prog': sys.argv[0]})
        sys.exit(1)

    if not o.uf_password:
        o.uf_password = 'admin'

    sql_queries = ''
    if o.sql == 'True':
        sql_queries="""-- BOTH
update attachment_config set name=%(attach_patch)s;
update res_users set password='"""+o.uf_password+"""';
update res_users set login='admin' where id=1;
update backup_config set beforeautomaticsync='f', beforemanualsync='f', afterautomaticsync='f', aftermanualsync='f', scheduledbackup='f', beforepatching='f';
-- INSTANCE
update ir_cron set active='f' where name in ('Automatic synchronization', 'Automatic backup', 'Send Remote Backup');
update automated_export set ftp_password='';
update automated_import set ftp_password='';
update ir_cron set active='f' where id in (select cron_id from automated_export);
update ir_cron set active='f' where id in (select cron_id from automated_import);
update ir_cron set nextcall='2100-01-01 00:00:00' where name='Update stock mission';
update sync_client_version set patch=NULL;
UPDATE sync_client_sync_server_connection SET database=%(server_db)s, host='127.0.0.1', login='admin', port=%(xmlrpc_port)s, protocol='xmlrpc', xmlrpc_retry=2, timeout=1200;
-- SERVER
UPDATE sync_server_entity SET hardware_id=%(hardware_id)s, user_id=1;"""
    elif not o.list and o.sql:
        f = open(o.sql, 'r')
        sql_queries = f.read()
        f.close()

    if o.upgrade:
        sql_queries = """update ir_module_module set state='to upgrade' where state='installed';
-- INSTANCE
delete from sync_client_version;
-- SERVER
delete from sync_server_version;
%s""" % (sql_queries,)

    if o.db_port:
        os.environ['PGPORT'] = o.db_port
    if o.db_user:
        os.environ['PGUSER'] = o.db_user
    if o.db_password:
        os.environ['PGPASSWORD'] = o.db_password
    if o.db_host:
        os.environ['PGHOST'] = o.db_host
    PG_param.set(o.db_user, o.db_password, o.db_host, o.db_port)
    transport = False
    if not o.sync_only:
        if o.issue:
            password = getpass.getpass('Jira Password : ')
            transport = JIRA(o.j_host, o.j_user, password, o.issue, o.include)
        elif o.from_dir:
            if os.path.abspath(o.from_dir) == os.path.abspath(o.directory):
                raise SystemExit("Input and Output dir can't be the same")
            transport = Directory(o.from_dir, o.include)
        elif o.rb:
            transport = RBIndex(o.rb, o.include)
        elif webdav and o.oc:
            transport = Owncloud(o.oc, o.oc_pass, o.include)
        elif o.postgres:
            if o.postgres == 'prod-dbs':
                o.postgres = 'uf7.unifield.org'
            transport = Postgres(o.postgres, o.postgres_cer, o.postgres_key, o.include)
        else:
            web_host = o.uf_web and o.uf_web.replace('http://','') or False
            if web_host and web_host.endswith('/'):
                web_host = web_host[0:-1]
            apache_prod_user = False
            apache_prod_password = False
            if 'production-dbs.uf5.unifield.org' in web_host or 'prod-dbs' in web_host:
                apache_prod_user = o.apache_prod_user
                apache_prod_password = o.apache_prod_password
            transport = Web(web_host, o.web_pass, o.include, apache_prod_user, apache_prod_password)

        dbs = transport.get_dbs()
        if o.list:
            sys.stdout.write("%s:\n" % transport.info)
            for db in dbs:
                sys.stdout.write(" - %s\n" % transport.get_db_name(db))
            if not dbs:
                sys.stdout.write(" no dump found\n")
            sys.exit(1)

        if not dbs:
            raise SystemExit("Dump not found, exit")

    if o.sync_only:
        dbs_name = []
        info = 'Daily light uf5'
    else:
        dbs_name = [transport.get_db_name(x) for x in dbs]
        info = transport.info
    if o.sync or o.sync_only:
        dbs_name.append('SYNC_LIGHT')

    add_info = []
    if o.drop:
        add_info.append("Drop existing dbs")
    if o.sql:
        add_info.append("Execute sql")
    if o.upgrade:
        add_info.append("Upgrade base module")

    if o.sync_run:
        if not has_oerplib:
            raise SystemExit('Unable to start a sync if oerplib is not installed')
        if not o.sync_port:
            raise SystemExit('Unable to start a sync if option --sync-port is missing')
        db_sync = o.sync_db
        if not db_sync:
            for db in dbs_name:
                if 'SYNC' in db:
                    db_sync = db
                    break
            if not db_sync:
                raise SystemExit('Unable to start a sync if SYNC SERVER DB is missing (add option --sync-db)')
        add_info.append('Start sync on port %s, db %s' % (o.sync_port, db_sync))

    if not o.auto_confirm:
        sys.stdout.write("%s\nDbs to restore:\n - %s\n%s\n" % (info, '\n - '.join(dbs_name), ' / '.join(add_info)))
        ret = ' '
        while ret.lower() not in ('', 'y', 'n'):
            ret = raw_input("Do you confirm ? [Y/n] ")
        if ret.lower() == 'n':
            raise SystemExit("Abort")
    if transport and isinstance(transport, Web):
        if 'SYNC_SERVER_XXX' in dbs_name:
            raise SystemExit("SYNC_SERVER_XXX ? Sorry it's too large ... please see (light) DAILY_SYNC_SERVER")
    sync_db = o.sync_db
    prefix = o.prefix
    threads = []
    if o.sync or o.sync_only:
        master_kind = {
            'with_master': 'SYNC_SERVER_LIGHT_WITH_MASTER',
            'no_master': 'SYNC_SERVER_LIGHT_NO_MASTER',
            'no_update': 'SYNC_SERVER_LIGHT_NO_UPDATE',
            '7days': 'SYNC_SERVER_LIGHT_7DAYS',
        }
        dump_name = master_kind.get(o.server_type, 'SYNC_SERVER_LIGHT_NO_MASTER')
        transport_ap = ApacheIndexes(user=o.apache_user, password=o.apache_password, dump_name=dump_name)
        sync_db, list_threads = restore_dump(transport_ap, prefix_db=prefix, output_dir=o.directory, sql_queries=sql_queries, drop=o.drop, sync_port=o.sync_port, upgrade=o.upgrade, passw=o.uf_password, removeprefix=o.remove_prefix)
        sync_db = sync_db[0]
        if list_threads:
            threads += list_threads
    if not o.sync_only:
        dbs, list_threads = restore_dump(transport, prefix_db=prefix, output_dir=o.directory, sql_queries=sql_queries, sync_db=sync_db, sync_port=o.sync_port, drop=o.drop, upgrade=o.upgrade, passw=o.uf_password, removeprefix=o.remove_prefix)
        if list_threads:
            threads += list_threads
            for x in threads:
                sys.stdout.write("Waiting end of modules upgrade\n")
                x.join()
            threads = []
        if o.sync_port:
            connect_and_sync(dbs, o.sync_port, o.sync_run, sync_db, o.uf_password)
    for x in threads:
        x.join()
