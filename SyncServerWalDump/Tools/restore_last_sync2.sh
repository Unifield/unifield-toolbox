#! /bin/bash

# To run this in cron, you need to give the password as an
# env variable:
#
# 50 1    * * *   sync-prod    HTTP_PASS=xxx /usr/local/bin/restore_last_sync.sh
#
# HTTP_PASS: the password on https://uf6.unifield.org/unifield_backups
#
# This script depends on psql_kill_active_connection.sh being
# available in /usr/local/bin. Use a symlink to make sure that's true.

DB=${1:-DAILY_SYNC_SERVER}
/etc/init.d/sync-prod-server stop > /dev/null
TABLESPACE="-D ssdspace"
#TABLESPACE=""

sudo -u postgres /usr/local/bin/psql_kill_active_connection.sh $DB
dropdb $DB
createdb ${TABLESPACE} $DB
psql -d $DB -c "CREATE SEQUENCE public.sync_client_version_id_seq START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;" > /dev/null
echo "`date` DATE psql start" > /home/sync-prod/DUMP/restore.log
lzma -d --stdout /home/sync-prod/DUMP/sync.data.lzma  | psql $DB >> /home/sync-prod/DUMP/restore.log 2>&1
lzma -d --stdout /home/sync-prod/DUMP/sync.schema.lzma  | psql $DB >> /home/sync-prod/DUMP/restore.log 2>&1
lzma -d --stdout /home/sync-prod/DUMP/sync_server_message.lzma  | psql $DB -c "TRUNCATE sync_server_message; COPY sync_server_message FROM STDIN WITH FREEZE;" >> /home/sync-prod/DUMP/restore.log 2>&1
lzma -d --stdout /home/sync-prod/DUMP/sync_server_update.lzma  | psql $DB -c "TRUNCATE sync_server_update; COPY sync_server_update FROM STDIN WITH FREEZE;" >> /home/sync-prod/DUMP/restore.log 2>&1

echo "`date` DATE psql end" >> /home/sync-prod/DUMP/restore.log
vacuumdb -Z -t sync_server_sync_rule -t sync_server_update -t sync_server_message $DB >> /dev/null 2> /dev/null

LIGHT_DB=$DB
pg_dump -Fc ${LIGHT_DB} > ~/exports/SYNC_SERVER_LIGHT_WITH_MASTER
echo "`date` DATE pg_dump end" >> /home/sync-prod/DUMP/restore.log

# ONLY MASTER
psql ${LIGHT_DB} <<EOF >> /dev/null
DELETE FROM sync_server_update u WHERE u.create_date < now() - interval '2 months';
EOF
pg_dump -Fc ${LIGHT_DB} > ~/exports/SYNC_SERVER_LIGHT_NO_MASTER
echo "`date` DATE pg_dump end" >> /home/sync-prod/DUMP/restore.log

# 7 days
psql ${LIGHT_DB} <<EOF >> /dev/null
DELETE FROM sync_server_update u WHERE u.create_date < now() - interval '7 days';
DELETE FROM sync_server_message WHERE create_date < now() - interval '7 days';
EOF
pg_dump -Fc ${LIGHT_DB} > ~/exports/SYNC_SERVER_LIGHT_7DAYS
echo "`date` DATE pg_dump end" >> /home/sync-prod/DUMP/restore.log

# NO UPDATE
# insert 1 fake update so last sequence is not 0
psql ${LIGHT_DB} <<EOF >> /dev/null
TRUNCATE sync_server_update;
TRUNCATE sync_server_message;
INSERT INTO sync_server_update (sequence) (SELECT number_next from ir_sequence where code='sync.server.update');
EOF
pg_dump -Fc ${LIGHT_DB} > ~/exports/SYNC_SERVER_LIGHT_NO_UPDATE
echo "`date` DATE pg_dump end" >> /home/sync-prod/DUMP/restore.log

/etc/init.d/sync-prod-server start > /dev/null

