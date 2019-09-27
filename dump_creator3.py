#!/usr/bin/python3.6

import os
import time
import shutil
import subprocess
import psycopg2
import webdav
import requests
import logging
import logging.handlers
import datetime
import sys
import config
import importlib

PSQL_DIR = config.psql_dir
DEST_DIR = config.dest_dir
SRC_DIR = config.src_dir
PSQL_CONF = os.path.join(DEST_DIR, 'psql_conf')
DUMP_DIR = os.path.join(DEST_DIR, 'DUMPS')
LOG_FILE = config.log_file
day_abr = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(message)s')

if LOG_FILE:
    handler = logging.handlers.RotatingFileHandler(LOG_FILE, 'a', 1024*1024, 365)
else:
    handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
handler.setFormatter(formatter)
logger.addHandler(handler)

def log(message):
    logger.info(message)

def error(message):
    logger.error(message)

def to_win(path):
    # internal cygwin commands use /cygdrive/c
    # external commands must use Win path C:
    return path.replace('/cygdrive/c', 'C:').replace('/cygdrive/d', 'D:')


def upload_od(file_path, oc):
    importlib.reload(config)

    dav_data = {
        'host': 'msfintl-my.sharepoint.com',
        'port': 443,
        'protocol': 'https',
        'username': 'UniField.MSF@geneva.msf.org',
        'password': config.password,
    }

    dav_data['path'] = config.path.get(oc, '/personal/unifield_msf_geneva_msf_org/documents/Test')
    max_retries = 10
    retries = 0
    buffer_size = 10 * 1024 * 1014
    file_name = os.path.basename(file_path)
    temp_file_name = 'Temp/%s'%file_name
    fileobj = open(file_path, 'rb')
    log('Start upload %s to %s '% (file_path, dav_data['path']))
    while True:
        try:
            dav = webdav.Client(**dav_data)
            dav.create_folder('Temp')
            upload_ok, error = dav.upload(fileobj, temp_file_name, buffer_size=buffer_size)
            if upload_ok:
                dav.move(temp_file_name, file_name)
                log('File uploaded')
                return True
            else:
                if retries > max_retries:
                    raise Exception(error)
                retries += 1
                time.sleep(2)
                if 'timed out' in error or '2130575252' in error:
                    log('OneDrive: session time out')
                    dav.login()

        except requests.exceptions.RequestException:
            if retries > max_retries:
                raise
            retries += 1
            time.sleep(2)

    fileobj.close()
    if not upload_ok:
        if error:
            raise Exception(error)
        else:
            raise Exception('Unknown error')
    return True

def un7zip(src_file, dest_dir, delete=False):
    if not os.path.isdir(dest_dir):
        raise Exception('un7zip: dest %s not found' % (dest_dir))
    command = ['/usr/bin/7z', 'e', src_file, '-y', '-bd', '-bb0', '-bso0', '-bsp0', '-o%s'%dest_dir]
    if delete:
        command.append('-sdel')
    log('Uncompress: %s ' % ' '.join(command))
    subprocess.check_output(command, stderr=subprocess.STDOUT)
    log('Done')

def process_directory():
    if not os.path.isdir(DUMP_DIR):
        os.makedirs(DUMP_DIR)
    for instance in os.listdir(SRC_DIR):
        if instance.startswith('.'):
            continue
        full_name = os.path.join(SRC_DIR, instance)
        try:
            if os.path.isdir(full_name):
                log('##### Instance %s'%full_name)

                dest_dir = os.path.join(DEST_DIR, instance)
                for dir_to_create in [os.path.join(dest_dir, 'OLDWAL')]:
                    if not os.path.isdir(dir_to_create):
                        log('Create %s'%dir_to_create)
                        os.makedirs(dir_to_create)

                dest_basebackup = os.path.join(dest_dir, 'base')
                pg_xlog = os.path.join(dest_basebackup, 'pg_xlog')

                # Copy / extract basbackup
                basebackup = os.path.join(full_name, 'base', 'base.tar.7z')
                if os.path.isfile(basebackup):
                    log('%s Found base backup %s'% (instance, basebackup))
                    if os.path.isdir(dest_basebackup):
                        # previous base found, rename it
                        shutil.move(dest_basebackup, os.path.join(dest_dir,'base_%s' % (time.strftime('%Y-%m-%d%H%M'))))
                        log('Move old base %s'%dest_basebackup)

                    new_base = os.path.join(dest_dir, 'base.tar.7z')
                    shutil.move(basebackup, new_base)
                    un7zip(new_base, dest_dir)
                    os.makedirs(dest_basebackup)
                    untar = ['tar', '-xf', os.path.join(dest_dir, 'base.tar'), '-C', dest_basebackup]
                    log(untar)
                    subprocess.check_output(untar, stderr=subprocess.STDOUT)
                    os.remove(os.path.join(dest_dir, 'base.tar'))

                    for conf in ['recovery.conf', 'postgresql.conf', 'pg_hba.conf']:
                        shutil.copy(os.path.join(PSQL_CONF, conf), dest_basebackup)

                    for del_recreate in [pg_xlog, os.path.join(dest_basebackup, 'pg_log')]:
                        if os.path.isdir(del_recreate):
                            shutil.rmtree(del_recreate)
                            os.makedirs(del_recreate)


                # Move WAL (copy + del to set right owner on target)
                wal_moved = 0
                if not os.path.exists(pg_xlog):
                    error('Unable to copy WAL, base directory not found %s' % pg_xlog)
                    continue
                for wal in os.listdir(full_name):
                    if wal.endswith('7z'):
                        wal_moved += 1
                        src_wal = os.path.join(full_name, wal)
                        un7zip(src_wal, pg_xlog)
                        os.remove(src_wal)

                log('%s, %d wal moved to %s' % (full_name, wal_moved, pg_xlog))

                if wal_moved:
                    try:
                        # Start psql
                        psql_start = [os.path.join(PSQL_DIR, 'pg_ctl.exe'), '-D', to_win(dest_basebackup), '-t', '60000', '-w', 'start']
                        log(' '.join(psql_start))
                        subprocess.run(psql_start, check=True)
                        #subprocess.check_output(psql_start)

                        db = psycopg2.connect('dbname=template1 host=127.0.0.1 user=openpg')
                        cr = db.cursor()
                        # wait end of wall processing
                        previous_wall = False
                        while True:
                            cr.execute("SELECT pg_last_xlog_replay_location()")
                            prev = cr.fetchone()[0]
                            if prev == previous_wall:
                                break
                            log('Wait recovery, previous: %s, current: %s' % (previous_wall, prev))
                            previous_wall = prev
                            time.sleep(2)

                        cr.execute("SELECT pg_last_xact_replay_timestamp()")
                        restore_date = cr.fetchone()[0]
                        if not restore_date:
                            label_file = os.path.join(dest_basebackup, 'backup_label.old')
                            if os.path.exists(label_file):
                                restore_date = datetime.datetime.fromtimestamp(os.path.getmtime(label_file))

                        if not restore_date:
                            restore_date = datetime.datetime.now()

                        cr.execute('SELECT datname FROM pg_database')
                        all_dbs = cr.fetchall()
                        db.close()
                        last_dump_file = os.path.join(dest_dir, 'last_dump.txt')
                        if os.path.exists(last_dump_file):
                            last_dump_date = datetime.datetime.fromtimestamp(os.path.getmtime(last_dump_file))
                            # only 1 dump per day
                            if last_dump_date.strftime('%Y-%m-%d') == time.strftime('%Y-%m-%d'):
                                log('%s already dumped today' % instance)
                                continue
                        # dump and zip the dump
                        for x in all_dbs:
                            if x[0] not in ['template0', 'template1', 'postgres']:
                                log('DB found %s'%x[0])
                                db = psycopg2.connect('dbname=%s host=127.0.0.1 user=openpg' % (x[0], ))
                                cr = db.cursor()
                                cr.execute('SELECT name FROM sync_client_version order by id desc limit 1')
                                version = cr.fetchone()[0] or 'XX'
                                cr.execute('SELECT oc FROM sync_client_entity')
                                oc = cr.fetchone()[0] or 'XX'
                                db.close()

                                dump_file = os.path.join(DUMP_DIR, '%s-%s-C-%s.dump' % (x[0], restore_date.strftime('%Y%m%d-%H%M%S'), version))
                                log('Dump %s' % dump_file)
                                pg_dump = [os.path.join(PSQL_DIR, 'pg_dump.exe'), '-h', '127.0.0.1', '-U', 'openpg', '-Fc', '-f', to_win(dump_file), x[0]]
                                subprocess.check_output(pg_dump, stderr=subprocess.STDOUT)

                                final_zip = os.path.join(DUMP_DIR, '%s-%s.zip' % (x[0], day_abr[datetime.datetime.now().weekday()]))
                                zip_c = ['zip', '-j', '-q', final_zip, dump_file]
                                log(' '.join(zip_c))
                                subprocess.call(zip_c)
                                os.remove(dump_file)
                                upload_od(final_zip, oc)
                                open(last_dump_file, 'wb').close()
                    finally:
                        psql_stop = [os.path.join(PSQL_DIR, 'pg_ctl.exe'), '-D', to_win(dest_basebackup), '-t', '60000', '-w', 'stop']
                        log(' '.join(psql_stop))
                        subprocess.run(psql_stop)

        except subprocess.CalledProcessError as e:
            error(e.output or e.stderr)
        except Exception as e:
            error(e)

if __name__ == '__main__':
    while True:
        process_directory()
        if sys.argv and len(sys.argv) > 1 and sys.argv[1] == '-1':
            log('Process ends')
            sys.exit(0)
        # TODO: OneDrive for each OC
        time.sleep(120)
