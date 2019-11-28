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
from dateutil.relativedelta import relativedelta
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

wal_forced = {}
if LOG_FILE:
    #handler = logging.handlers.RotatingFileHandler(LOG_FILE, 'a', 1024*1024, 365)
    handler = logging.handlers.TimedRotatingFileHandler(LOG_FILE, when='midnight')
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

    if oc not in config.path:
        error('%s unknown oc %s' % (file_path, oc))
    dav_data['path'] = config.path.get(oc, '/personal/unifield_msf_geneva_msf_org/documents/Test')
    max_retries = 10
    retries = 0
    buffer_size = 10 * 1024 * 1014
    file_name = os.path.basename(file_path)
    temp_file_name = 'Temp/%s'%file_name
    fileobj = open(file_path, 'rb')
    log('Start upload %s to %s '% (file_path, dav_data['path']))
    upload_ok = False
    dav_error = False
    while True:
        try:
            dav = webdav.Client(**dav_data)
            dav.create_folder('Temp')
            upload_ok, dav_error = dav.upload(fileobj, temp_file_name, buffer_size=buffer_size)
            if upload_ok:
                dav.move(temp_file_name, file_name)
                log('File %s uploaded' % (file_path,))
                return True
            else:
                if retries > max_retries:
                    raise Exception(dav_error)
                retries += 1
                time.sleep(2)
                if 'timed out' in dav_error or '2130575252' in dav_error:
                    log('%s OneDrive: session time out' % (file_path,))
                    dav.login()

        except requests.exceptions.RequestException:
            if retries > max_retries:
                raise
            retries += 1
            time.sleep(2)

    fileobj.close()
    if not upload_ok:
        if dav_error:
            raise Exception(dav_error)
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

def process_directory():
    if not os.path.isdir(DUMP_DIR):
        os.makedirs(DUMP_DIR)
    for instance in os.listdir(SRC_DIR):
        if instance.startswith('.'):
            continue
        full_name = os.path.join(SRC_DIR, instance)
        try:
            if os.path.isdir(full_name):
                #log('##### Instance %s'%full_name)

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
                    old_base_moved = False
                    if os.path.isdir(dest_basebackup):
                        # previous base found, rename it
                        old_base_moved = os.path.join(dest_dir,'base_%s' % (time.strftime('%Y-%m-%d%H%M')))
                        shutil.move(dest_basebackup, old_base_moved)
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

                    if old_base_moved:
                        # old base moved, copy previous WAL in the new basebackup
                        # case of WAL created during this base backup was already moved to the old WAL
                        shutil.rmtree(pg_xlog)
                        shutil.copytree(os.path.join(old_base_moved, 'pg_xlog'), pg_xlog)

                # is there an in-progress rsync ?
                rsync_temp = os.path.join(full_name, '.rsync-partial')
                if os.path.exists(rsync_temp):
                    partial_modification_date = datetime.datetime.fromtimestamp(os.path.getctime(rsync_temp))
                    if partial_modification_date > datetime.datetime.now() + relativedelta(minutes=-10):
                        log('%s, rsync in progess %s' % (full_name, partial_modification_date.strftime('%Y-%m-%d %H:%M')))
                        continue

                # Move WAL (copy + del to set right owner on target)
                if not os.path.exists(pg_xlog):
                    log('Unable to copy WAL, base directory not found %s' % pg_xlog)
                    continue

                wal_moved = 0
                forced_wal = False
                forced_dump = False
                retry = True
                while retry:
                    retry_wal = False
                    for_next_loop = False
                    for wal in os.listdir(full_name):
                        full_path_wal = os.path.join(full_name, wal)
                        if wal.endswith('7z'):
                            wal_moved += 1
                            un7zip(full_path_wal, pg_xlog)
                            os.remove(full_path_wal)
                        elif wal == 'force_dump':
                            os.remove(full_path_wal)
                            forced_dump = True
                        elif wal.startswith('.') and '.7z.' in wal:
                            # there is an inprogress rsync
                            try:
                                partial_modification_date = datetime.datetime.fromtimestamp(os.path.getctime(full_path_wal))
                                if partial_modification_date > datetime.datetime.now() + relativedelta(minutes=-45):
                                    # rsync inprogress is less than X min, go to the next instance
                                    log('%s found %s, next_loop (%s)' % (full_name, wal, partial_modification_date.strftime('%Y-%m-%d %H:%M')))
                                    for_next_loop = True
                                    break
                                else:
                                    # inprogress is more than X min: too slow, generate backup
                                    log('%s found %s, too old, force wal (%s)' % (full_name, wal, partial_modification_date.strftime('%Y-%m-%d %H:%M')))
                                    if not wal_forced.get(full_name, {}).get(full_path_wal):
                                        wal_forced[full_name] = {full_path_wal: True}
                                        forced_wal = True
                            except FileNotFoundError:
                                # between listdir and getctime the temp file has been removed, retry listdir
                                log('%s file not found %s, retry' % (full_name, wal))
                                retry_wal = True
                                break
                    retry = retry_wal

                if for_next_loop:
                    continue

                if wal_moved:
                    log('%s, %d wal moved to %s' % (full_name, wal_moved, pg_xlog))
                elif forced_wal:
                    log('%s, wal forced' % (full_name, ))
                elif forced_dump:
                    log('%s, dump forced' % (full_name, ))

                if forced_wal or forced_dump or wal_moved:
                    try:
                        # Start psql
                        psql_start = [os.path.join(PSQL_DIR, 'pg_ctl.exe'), '-D', to_win(dest_basebackup), '-t', '1200', '-w', 'start']
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
                            log('%s wait recovery, previous: %s, current: %s' % (instance, previous_wall, prev))
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
                        last_wal_date = False
                        if not forced_dump and os.path.exists(last_dump_file):
                            last_dump_date = datetime.datetime.fromtimestamp(os.path.getmtime(last_dump_file))
                            with open(last_dump_file) as last_desc:
                                last_wal_date = last_desc.read()
                            # only 1 dump per day
                            if last_dump_date.strftime('%Y-%m-%d') == time.strftime('%Y-%m-%d'):
                                log('%s already dumped today' % instance)
                                continue

                        if forced_wal and last_wal_date and last_wal_date == restore_date.strftime('%Y%m%d-%H%M%S'):
                            # same wal as previous dump: do noting (the in-progess wal is the 1st one)
                            log('%s : same data (%s) as previous backup (%s), do not dump/push to od' % (instance, last_wal_date, restore_date.strftime('%Y%m%d-%H%M%S')))
                            continue

                        # dump and zip the dump
                        for x in all_dbs:
                            if x[0] not in ['template0', 'template1', 'postgres']:
                                log('%s db found %s'% (instance, x[0]))
                                db = psycopg2.connect('dbname=%s host=127.0.0.1 user=openpg' % (x[0], ))
                                cr = db.cursor()
                                cr.execute('SELECT name FROM sync_client_version where date is not null order by date desc limit 1')
                                version = cr.fetchone()[0]
                                if not version:
                                    error('%s: version not found' % instance)
                                    version = 'XX'
                                cr.execute('SELECT oc FROM sync_client_entity')
                                oc = cr.fetchone()[0]
                                if not oc:
                                    error('%s: OC not found' % instance)
                                    oc = 'XX'
                                db.close()

                                dump_file = os.path.join(DUMP_DIR, '%s-%s-C-%s.dump' % (x[0], restore_date.strftime('%Y%m%d-%H%M%S'), version))
                                log('Dump %s' % dump_file)
                                pg_dump = [os.path.join(PSQL_DIR, 'pg_dump.exe'), '-h', '127.0.0.1', '-U', 'openpg', '-Fc', '-f', to_win(dump_file), x[0]]
                                subprocess.check_output(pg_dump, stderr=subprocess.STDOUT)

                                final_zip = os.path.join(DUMP_DIR, '%s-%s.zip' % (x[0], day_abr[datetime.datetime.now().weekday()]))
                                if os.path.exists(final_zip):
                                    os.remove(final_zip)

                                zip_c = ['zip', '-j', '-q', final_zip, dump_file]
                                log(' '.join(zip_c))
                                subprocess.call(zip_c)
                                os.remove(dump_file)
                                upload_od(final_zip, oc)
                                with open(last_dump_file, 'w') as last_desc:
                                    last_desc.write(restore_date.strftime('%Y%m%d-%H%M%S'))
                    finally:
                        psql_stop = [os.path.join(PSQL_DIR, 'pg_ctl.exe'), '-D', to_win(dest_basebackup), '-t', '1200', '-w', 'stop']
                        log(' '.join(psql_stop))
                        subprocess.run(psql_stop)

        except subprocess.CalledProcessError as e:
            error(e.output or e.stderr)
        except Exception:
            logger.exception('ERROR')

if __name__ == '__main__':
    while True:
        log('Check directories')
        process_directory()
        if sys.argv and len(sys.argv) > 1 and sys.argv[1] == '-1':
            log('Process ends')
            sys.exit(0)

        log('sleep')
        time.sleep(120)
