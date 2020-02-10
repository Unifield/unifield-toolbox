#!/opt/sync_dump_env/bin/python3

import psycopg2
import subprocess
import time
import logging
import logging.handlers
import sys
import os

LOG_FILE='/tmp/log'
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(message)s')
handler = logging.handlers.TimedRotatingFileHandler(LOG_FILE, when='midnight')
handler.setLevel(logging.INFO)
handler.setFormatter(formatter)
logger.addHandler(handler)



logger.info('Start')
#get_wal = ['rsync', '-a', 'root@212.95.73.128:/opt/WAL/', '/opt/WAL/']
get_wal = ['rsync', '-a', '--remove-source-files', 'root@212.95.73.128:/opt/WAL/', '/opt/WAL/']
subprocess.check_output(get_wal, stderr=subprocess.STDOUT)
logger.info('Wal copied')

try:
    psql_start = ['/opt/psql-10/bin/pg_ctl', '-D', '/opt/SYNC/sync_prod/main/', '-t', '1200', '-w', 'start']
    subprocess.run(psql_start, check=True)
    logger.info('Main psql started')
    db = psycopg2.connect('dbname=template1 host=127.0.0.1 user=openerp')
    cr = db.cursor()
    previous_wall = False
    while True:
        time.sleep(6)
        cr.execute("SELECT pg_last_wal_replay_lsn()")
        prev = cr.fetchone()[0]
        logger.info('Last wal %s' % (prev, ))
        if prev == previous_wall:
            break
        previous_wall = prev

    logger.info('WAL Replayed')
    for todel in ['sync.data.lzma', 'sync.schema.lzma', 'sync_server_message.lzma']:
        full_todel = os.path.join('/opt/SYNC/DUMP', todel)
        if os.path.exists(full_todel):
            os.remove(full_todel)

    subprocess.run('/opt/SYNC/dump_db.bash')
except subprocess.CalledProcessError as e:
    logger.error(e.output or e.stderr)
finally:
    psql_stop = ['/opt/psql-10/bin/pg_ctl', '-D', '/opt/SYNC/sync_prod/main/', '-t', '1200', '-w', 'stop']
    subprocess.run(psql_stop)
    logger.info('Main psql stopped')

sys.exit()
