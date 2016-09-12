#! /usr/bin/python
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
            elif x in name:
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
    host = 'sync-prod_dump.uf5.unifield.org'
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


class Web(object):

    default_host = 'unifield-%s.ocg.msf.org:8061'
    default_password = 'bkAdmin'
    default_rb_password = '4unifield'

    def __init__(self, host, password, include_dbs):
        if host:
            if len(host) == 3:
                host = self.default_host % host
        else:
            host = self.default_host % 'ct1'

        if not password and (host.endswith('unifield.org') or host.endswith('unifield.biz')):
            password = self.default_rb_password

        url = 'http://%s/' % (host,)
        self.password = password or self.default_password
        self.backup_url = '%sopenerp/database/do_backup' % (url, )
        self.headers = {
            'Referer': '%sopenerp/database/backup' % (url, ),
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        cnx = httplib2.Http()
        resp, content = cnx.request('%sopenerp/database/backup' % (url, ) , "GET")
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
        cnx = httplib2.Http()
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
        j_obj = jira.JIRA(self.host, options={'check_update': False}, basic_auth=(user, password))
        self.issue = j_obj.issue(issue_key)
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
                netrpc = oerplib.OERP('127.0.0.1', protocol='netrpc', port=sync_port, database=db)
                sys.stdout.write("%s: Connect to sync\n" % (db, ))
                netrpc.login(uf_pass, uf_pass)
                conn_manager = netrpc.get('sync.client.sync_server_connection')
                conn_ids = conn_manager.search([])
                conn_manager.write(conn_ids, {'password': uf_pass})
                conn_manager.connect()
                if o.sync_run:
                    netrpc.get('sync.client.entity').sync_manual_threaded()
                    sys.stdout.write("Start sync\n")
            except Exception, e:
                sys.stderr.write("%s: unable to sync connect\n%s\n" % (db, e))
    return True

def restore_dump(transport, prefix_db, output_dir=False, sql_queries=False, sync_db=False, sync_port=0 , drop=False):
    restored = []
    sql_data = {
        'hardware_id': get_harware_id(),
        'netrpc_port': sync_port or 8061,
        'server_db': sync_db or 'SYNC_SERVER',
    }
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
        transport.write_dump(db, f)
        f.close()

        if not os.path.getsize(file_name):
            sys.stderr.write("Warning:%s dump %s is empty !\n" % (dump_name, file_name))
            continue

        new_db_name = dump_name
        if prefix_db:
            new_db_name = '%s_%s' % (prefix_db, new_db_name)
        new_db_name = re.sub('-[0-9]{6}(-(A|B|BP))?-UF.*.dump$', '', new_db_name).replace(' ','_')
        new_db_name = re.sub('.dump$', '', new_db_name)
        orig_db_name = new_db_name
        ok = False
        i = 1
        # check if db exists
        while not ok:
            try:
                db_conn = psycopg2.connect(PG_param.get_dsn(new_db_name))
                if drop:
                    db_conn.close()
                    call(['dropdb', new_db_name])
                    sys.exit(0)
                    break
                new_db_name = '%s_%s' % (orig_db_name, i)
                db_conn.close()
                i += 1
            except:
                ok = True
        sys.stdout.write("restore %s\n" % new_db_name)
        call(['createdb', new_db_name])
        call(['pg_restore', '--no-owner', '--no-acl', '-d', new_db_name, file_name])
        restored.append(new_db_name)
        sys.stdout.write("restored\n")
        if not output_dir:
            os.remove(file_name)

        is_server_db = 'SYNC' in new_db_name
        query_for_server = None
        if sql_queries:
            sys.stdout.write("execute sql queries\n")
            db_conn = psycopg2.connect(PG_param.get_dsn(new_db_name))
            cr = db_conn.cursor()
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
            db_conn.close()

    return restored

if __name__ == "__main__":
    defaults = {
        'j_host': 'http://jira.unifield.org',
        'sync_port': '8070',
        'prefix': getpass.getuser(),
        'uf_password': 'admin',
    }
    rcfile = '~/.restore_dumprc'
    cfile = os.path.realpath(os.path.expanduser(rcfile))
    if os.path.exists(cfile):
        config = ConfigParser.SafeConfigParser()
        config.read([cfile])
        defaults.update(dict(config.items("Restore")))

    parser = argparse.ArgumentParser()
    parser.set_defaults(**defaults)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--examples', action='store_true', help='show usage examples and exit')
    group.add_argument('-j', '--issue', action='store', help='restore from Jira Issue Key')
    group.add_argument('-d', '--from-dir', action='store', help='restore dump from directory')
    group.add_argument('-f', '--uf-web', metavar='HOST[:PORT]', nargs='?', default=' ', help="UniField Web host:port default: ct1")
    group.add_argument('--rb', metavar='HOST[:PORT]', help="From mkdb rb_dump exports")
    group.add_argument('--sync-only', action='store_true', help='restore *only* light sync')

    parser.add_argument("--include", "-i", metavar="DB1,DB2", default='', help="comma separated list of dbs to restore (postfix db_name with + for exact match)")
    parser.add_argument("--uf-password", action='store', help="UniField admin login & password")
    parser.add_argument("--drop", action='store_true', help="drop db if exists")
    parser.add_argument('-o', '--directory', action='store', default='', help='save dumps to directory')
    parser.add_argument('--sql', nargs='?', default='True',  action='store', help='sql file to execute, set empty to disable default sql execution')

    parser.add_argument('-l', '--list', action='store_true', help='list dumps and exit')
    parser.add_argument('--prefix', nargs='?', metavar="DB PREFIX", help="prefix dbname by a string (set empty to disable) [default: user]")
    parser.add_argument('--sync-port', help='sync netrpc port, used to update instances [default: %(default)s]')
    parser.add_argument('--sync-db', help='sync server db, used to update instances [default: %(default)s]')
    parser.add_argument('--sync-run', action="store_true", help='try to start sync')
    parser.add_argument('--db-port', action="store", help='PSQL port')
    parser.add_argument('--db-user', action="store", help='PSQL user')
    parser.add_argument('--db-password', action="store", help='PSQL Password')
    parser.add_argument('--db-host', action="store", help='PSQL Host')

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

    sync_parser = parser.add_argument_group('Restore Sync Server Light')
    sync_parser.add_argument("--server-type", "-t", choices=['no_master', 'with_master', 'no_update'], default='no_master', help="kind of sync server dump to restore: no_master: only the last 2 months upd/msg, with_master: last 2 months upd/msg + master updates, no_update: empty sync server without any upd/msg, [default: %(default)s]")

    o = parser.parse_args()
    if o.examples:
        sys.stdout.write(examples % {'prog': sys.argv[0]})
        sys.exit(1)

    if not o.uf_password:
        o.uf_password = 'admin'
    sql_queries = ''
    if o.sql == 'True':
        sql_queries="""update res_users set password='"""+o.uf_password+"""';
update res_users set login='"""+o.uf_password.lower()+"""' where id=1;
update backup_config set beforeautomaticsync='f', beforemanualsync='f', afterautomaticsync='f', aftermanualsync='f', scheduledbackup='f', beforepatching='f';
-- INSTANCE
update ir_cron set active='f' where name in ('Automatic synchronization', 'Automatic backup', 'Update stock mission');
update sync_client_version set patch=NULL;
UPDATE sync_client_sync_server_connection SET database=%(server_db)s, host='127.0.0.1', login='"""+o.uf_password+"""', port=%(netrpc_port)s, protocol='netrpc';
-- SERVER
UPDATE sync_server_entity SET hardware_id=%(hardware_id)s, user_id=1;"""
    elif not o.list and o.sql:
        f = open(o.sql, 'r')
        sql_queries = f.read()
        f.close()

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
        else:
            web_host = o.uf_web and o.uf_web.replace('http://','') or False
            transport = Web(web_host, o.web_pass, o.include)

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
        if not o.trust_me_i_know_what_i_m_doing and len(dbs_name) > 5:
            raise SystemExit("If you really need to restore more than 5 dbs from a Web Instance add the option --trust-me-i-know-what-i-m-doing to the script")
    sync_db = o.sync_db
    prefix = o.prefix
    if o.sync or o.sync_only:
        master_kind = {
            'with_master': 'SYNC_SERVER_LIGHT_WITH_MASTER',
            'no_master': 'SYNC_SERVER_LIGHT_NO_MASTER',
            'no_update': 'SYNC_SERVER_LIGHT_NO_UPDATE',
        }
        dump_name = master_kind.get(o.server_type, 'SYNC_SERVER_LIGHT_NO_MASTER')
        transport_ap = ApacheIndexes(user=o.apache_user, password=o.apache_password, dump_name=dump_name)
        sync_db = restore_dump(transport_ap, prefix_db=prefix, output_dir=o.directory, sql_queries=sql_queries, drop=o.drop)[0]

    if not o.sync_only:
        dbs = restore_dump(transport, prefix_db=prefix, output_dir=o.directory, sql_queries=sql_queries, sync_db=sync_db, sync_port=o.sync_port, drop=o.drop)
        if o.sync_port:
            connect_and_sync(dbs, o.sync_port, o.sync_run, sync_db, o.uf_password)
