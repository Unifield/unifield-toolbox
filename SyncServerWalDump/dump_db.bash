#! /bin/bash

PG_DUMP='/opt/psql-10/bin/pg_dump  -h 127.0.0.1 -p 5432 -U openerp'
PSQL='/opt/psql-10/bin/psql  -h 127.0.0.1 -p 5432 -U openerp -d SYNC_SERVER'
UF5_CONFIG='sync-prod@uf5.rb.unifield.org'
$PG_DUMP -T sync_server_entity_rel -T sync_server_update -T sync_server_message -Fp SYNC_SERVER  | lzma -2 - > /opt/SYNC/DUMP/sync.data.lzma
$PG_DUMP -s -t sync_server_entity_rel -t sync_server_update -t sync_server_message -Fp SYNC_SERVER  | lzma -2 - > /opt/SYNC/DUMP/sync.schema.lzma

$PSQL -c "COPY (SELECT * from  sync_server_message WHERE create_date >= now() - interval '2 months') TO STDOUT;" | lzma -2 - > /opt/SYNC/DUMP/sync_server_message.lzma
$PSQL -c "COPY  (SELECT * from sync_server_update u WHERE u.rule_id IN (SELECT id FROM sync_server_sync_rule WHERE active !='f' AND master_data!='f') OR u.create_date >= now() - interval '2 months') TO STDOUT;" | lzma -2 - > /opt/SYNC/DUMP/sync_server_update.lzma
scp -B /opt/SYNC/DUMP/*lzma $UF5_CONFIG:/home/sync-prod/DUMP
ssh -n -f $UF5_CONFIG "sh -c 'nohup /usr/local/bin/restore_last_sync2.sh > /dev/null 2>&1 &'"
