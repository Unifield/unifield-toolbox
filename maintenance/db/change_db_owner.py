import sys
import psycopg2

dbname = sys.argv[1]
target_user = sys.argv[2]

db1 = psycopg2.connect(dbname=dbname)
cr1 = db1.cursor()

cr1.execute('alter database "%s" owner to "%s"' % (dbname, target_user))
cr1.execute("select tablename from pg_tables where schemaname = 'public'")
for xx in cr1.fetchall():
    cr1.execute('alter table "%s" owner to "%s"' % (xx[0], target_user))

cr1.execute("select sequence_name from information_schema.sequences where sequence_schema = 'public'")
for xx in cr1.fetchall():
    cr1.execute('alter table "%s" owner to "%s"' % (xx[0], target_user))

cr1.execute("select table_name from information_schema.views where table_schema = 'public'")
for xx in cr1.fetchall():
    cr1.execute('alter table "%s" owner to "%s"' % (xx[0], target_user))

cr1.execute("SELECT format('%I.%I(%s)', ns.nspname, p.proname, oidvectortypes(p.proargtypes)) FROM pg_proc p INNER JOIN pg_namespace ns ON (p.pronamespace = ns.oid) WHERE ns.nspname = 'public'")
for xx in cr1.fetchall():
    cr1.execute('alter function %s owner to "%s"' % (xx[0], target_user))

db1.commit()

