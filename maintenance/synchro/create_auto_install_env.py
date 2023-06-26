import sys
import psycopg2
import os
import ConfigParser
import shutil

home = os.path.expanduser('~')
SRC_INI = os.path.join(home, 'unifield-server/tools/UFautoInstall/uf_auto_install.conf')
DEST_DIR = os.path.join(home, 'unifield-server/UFautoInstall')
DEST_INI = os.path.join(DEST_DIR, 'uf_auto_install.conf')

if not os.path.exists(DEST_DIR):
    os.makedirs(DEST_DIR)
if not os.path.exists(os.path.join(DEST_DIR, 'import')):
    shutil.copytree(os.path.join(home, 'unifield-server/tools/UFautoInstall/import'), os.path.join(DEST_DIR, 'import'))

# /opt/unifield-toolbox/restore_dump.py --sync-only --upgrade --server-type=with_master


if len(sys.argv) < 2:
    print("instance name required")
    sys.exit(1)

dsn='dbname=postgres'
db = psycopg2.connect(dsn)
cr = db.cursor()


server_db = False
cr.execute("SELECT datname FROM pg_database WHERE pg_get_userbyid(datdba) = current_user")
for x in cr.fetchall():
    if 'SYNC' in x[0]:
        server_db = x[0]

db.close()
db = psycopg2.connect('dbname=%s'%server_db)
db.set_isolation_level(3)
cr = db.cursor()

if not server_db:
    print("Sync db not found")
    sys.exit(1)

cr.execute("""
            select
                e.id, e.oc, e.name, p.name, array_agg(g.name)
            from
                sync_server_entity e,
                sync_entity_group_rel r,
                sync_server_entity_group g,
                sync_server_entity p
            where
                e.id = r.entity_id
                and r.group_id=g.id
                and e.parent_id = p.id
                and e.name=%s
            group by e.id, e.oc, e.name, p.name
        """, (sys.argv[1], ))
if not cr.rowcount:
    print("Instance %s not found", sys.argv[1])
    sys.exit(1)

d = cr.fetchone()
print d

cr.execute('''
    select
        values
    from
        sync_server_update
    where
        model='msf.instance'
        and fields like '%''code'', ''instance''%'
        and values like '%'''+sys.argv[1]+'''%'
    ''')

x = eval(cr.fetchone()[0])
instance_code = x[0]
instance_level = x[3]


config = ConfigParser.ConfigParser()
config.read(SRC_INI)
config.set('instance', 'rb_prefix', '%s_' % os.environ['USER'])
config.set('instance', 'sync_port', os.environ['XMLRPCPORT'])
config.set('instance', 'db_name', '%s_%s' % (os.environ['USER'], sys.argv[1]))
config.set('instance', 'instance_name', sys.argv[1])
config.set('instance', 'prop_instance_code', instance_code)
config.set('instance', 'admin_password', os.environ['ADMINPASSWORD'])
config.set('instance', 'sync_user', 'admin')
config.set('instance', 'sync_pwd', os.environ['ADMINPASSWORD'])
config.set('instance', 'sync_server', server_db)
config.set('instance', 'sync_host', '127.0.0.1')
config.set('instance', 'oc', d[1])
config.set('instance', 'parent_instance', d[3])
config.set('instance', 'group_names', ','.join(d[4]))
config.set('instance', 'instance_level', instance_level)

with open(DEST_INI, 'w') as configfile:
    config.write(configfile)

cr.execute("select min(id) from sync_server_update where source=%s", (d[0], ))
min_id = cr.fetchone()[0]
print('Delete min update %s'%min_id)
cr.execute("delete from sync_server_update where id>=%s", (min_id, ))
cr.execute("update sync_server_entity set name=name||'_KO' where id=%s", (d[0], ))

db.commit()
cr.close()
