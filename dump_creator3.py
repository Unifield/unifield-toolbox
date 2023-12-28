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
import heapq
import threading
import itertools

PSQL_DIR = config.psql_dir
DEST_DIR = config.dest_dir
SRC_DIR = config.src_dir
PSQL_CONF = os.path.join(DEST_DIR, 'psql_conf')
DUMP_DIR = os.path.join(DEST_DIR, 'DUMPS')
# TODO
TOUCH_FILE_DUMP = os.path.join(DUMP_DIR, 'touch_dump-new')
TOUCH_FILE_LOOP = os.path.join(DUMP_DIR, 'touch_loop-new')
LOG_FILE = config.log_file
day_abr = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


def to_win(path):
    # internal cygwin commands use /cygdrive/c
    # external commands must use Win path C:
    return path.replace('/cygdrive/c', 'C:').replace('/cygdrive/d', 'D:')



class Queue():
    lock = threading.RLock()
    queue = []
    list_items = {}
    counter = itertools.count()

    def add(self, item, prio=1):
        with self.lock:
            if item not in self.list_items:
                self.list_items[item] = prio
                heapq.heappush(self.queue, [prio, next(self.counter), item])
            elif self.list_items[item] <= prio:
                return
            else:
                for t in self.queue:
                    if t[1] == item:
                        t[0] = 0 # delete item
                self.list_items[item] = prio
                heapq.heappush(self.queue, [prio, next(self.counter), item])

    def pop(self):
        with self.lock:
            prio = 0
            while prio == 0:
                try:
                    prio, timest, item = heapq.heappop(self.queue)
                except IndexError:
                    # empty queue
                    return False, False
                try:
                    del self.list_items[item]
                except KeyError:
                    pass
            return prio, item

    def resfresh(self):
        with self.lock:
            forced_path = os.path.join(SRC_DIR, 'forced_instance_new')
            if os.path.exists(forced_path):
                with open(forced_path) as forced_path_desc:
                    instance = forced_path_desc.read()
                self.add(instance, -2)
                os.remove(forced_path)

            for instance in sorted(os.listdir(SRC_DIR)):
                if instance.startswith('.'):
                    continue
                newbase = os.path.isfile(os.path.join(SRC_DIR, instance, 'base', 'base.tar.7z'))
                if newbase:
                    self.add(instance, -1)
                else:
                    self.add(instance)

def stopped(delete=False):
    # TODO
    stop_service = os.path.join(SRC_DIR, 'stop_service_new')
    if os.path.exists(stop_service):
        if delete:
            os.remove(stop_service)
            return True
    return False

class Process():

    def __init__(self, thread, queue):
        self.thread = thread
        self.queue = queue

        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(message)s')

        if LOG_FILE:
            handler = logging.handlers.TimedRotatingFileHandler('%s-%s' % (thread, LOG_FILE), when='midnight')
        else:
            handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log(self, message):
        self.logger.info(message)

    def error(self, message):
        self.logger.error(message)

    def un7zip(self, src_file, dest_dir, delete=False):
        if not os.path.isdir(dest_dir):
            raise Exception('un7zip: dest %s not found' % (dest_dir))
        command = ['/usr/bin/7z', 'e', src_file, '-y', '-bd', '-bb0', '-bso0', '-bsp0', '-o%s'%dest_dir]
        if delete:
            command.append('-sdel')
        self.log('Uncompress: %s ' % ' '.join(command))
        subprocess.check_output(command, stderr=subprocess.STDOUT)

    def upload_od(self, file_path, oc):
        importlib.reload(config)

        dav_data = {
            'host': 'msfintl-my.sharepoint.com',
            'port': 443,
            'protocol': 'https',
            'username': 'UniField.MSF@geneva.msf.org',
            'password': config.password,
        }

        if oc not in config.path:
            self.error('%s unknown oc %s' % (file_path, oc))
        dav_data['path'] = config.path.get(oc, '/personal/unifield_msf_geneva_msf_org/documents/Test')
        max_retries = 3
        retries = 0
        buffer_size = 10 * 1024 * 1014
        file_name = os.path.basename(file_path)
        temp_file_name = 'Temp/%s'%file_name
        fileobj = open(file_path, 'rb')
        self.log('Start upload %s to %s '% (file_path, dav_data['path']))
        upload_ok = False
        dav_error = False
        dav_connected = False
        temp_created = False
        while True:
            try:
                if not dav_connected:
                    fileobj.seek(0)
                    dav = webdav.Client(**dav_data)
                    dav_connected = True
                    self.log('Dav connected')
                    retries = 0

                if not temp_created:
                    try:
                        dav.create_folder('Temp')
                    except:
                        self.log('Except Temp')
                        if retries > max_retries:
                            raise
                        retries += 1
                        time.sleep(2)
                    temp_created = True
                    self.log('Temp OK')
                    retries = 0

                if not upload_ok:
                    upload_ok, dav_error = dav.upload(fileobj, temp_file_name, buffer_size=buffer_size)

                if upload_ok:
                    self.log('Moving File')
                    try:
                        dav.delete(file_name)
                        dav.move(temp_file_name, file_name)
                    except:
                        self.log('Except move')
                        if retries > max_retries:
                            raise
                        retries += 1
                        time.sleep(2)
                    self.log('File %s uploaded' % (file_path,))
                    return True
                else:
                    self.log('Dav 1 retry')
                    if retries > max_retries:
                        raise Exception(dav_error)
                    retries += 1
                    time.sleep(2)
                    if dav_connected and 'timed out' in dav_error or '2130575252' in dav_error:
                        self.log('%s OneDrive: session time out' % (file_path,))
                        dav.login()

            except (requests.exceptions.RequestException, webdav.ConnectionFailed):
                self.log('Dav 2 retry')
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

    def process_directory(self):
        if not os.path.isdir(DUMP_DIR):
            os.makedirs(DUMP_DIR)

        psql_port = 5432 + self.thread
        while True:
            if stopped():
                self.log('Stopped')
                return False

            self.queue.resfresh()

            nb, instance = self.queue.pop()
            if not instance or instance == 'INIT':
                self.log('sleep')
                time.sleep(10)
                if instance == 'INIT':
                    with open(TOUCH_FILE_LOOP, 'w') as t_file:
                        t_file.write(time.strftime('%Y-%m-%d%H%M%S'))
                    self.queue.add('INIT')
                continue


            forced_instance = False
            if nb < 0:
                self.log('Forced instance %s' % (instance, ))
                forced_instance = True


            # TODO
            continue


            full_name = os.path.join(SRC_DIR, instance)
            try:
                if os.path.isdir(full_name):
                    basebackup = os.path.join(full_name, 'base', 'base.tar.7z')
                    dest_dir = os.path.join(DEST_DIR, instance)

                    if not os.path.isdir(dest_dir) and not os.path.isfile(basebackup):
                        # new instance wait for base.tar
                        continue

                    for dir_to_create in [os.path.join(dest_dir, 'OLDWAL')]:
                        if not os.path.isdir(dir_to_create):
                            self.log('Create %s'%dir_to_create)
                            os.makedirs(dir_to_create)

                    dest_basebackup = os.path.join(dest_dir, 'base')
                    pg_xlog = os.path.join(dest_basebackup, 'pg_xlog')
                    pg_wal = os.path.join(dest_basebackup, 'pg_wal')
                    oldwal = os.path.join(dest_dir, 'OLDWAL')

                    if os.path.isdir(dest_basebackup):
                        # copy postgres and recovery / migration of new WAL destination
                        for conf in ['recovery.conf', 'postgresql.conf']:
                            shutil.copy(os.path.join(PSQL_CONF, conf), dest_basebackup)

                    # Copy / extract basbackup
                    basebackup_found = False
                    if os.path.isfile(basebackup):
                        self.log('%s Found base backup %s'% (instance, basebackup))
                        old_base_moved = False
                        if os.path.isdir(dest_basebackup):
                            # previous base found, rename it
                            old_base_moved = os.path.join(dest_dir,'base_%s' % (time.strftime('%Y-%m-%d%H%M')))
                            shutil.move(dest_basebackup, old_base_moved)
                            self.log('Move old base %s'%dest_basebackup)

                        new_base = os.path.join(dest_dir, 'base.tar.7z')
                        shutil.move(basebackup, new_base)
                        self.un7zip(new_base, dest_dir)
                        os.makedirs(dest_basebackup)
                        untar = ['tar', '-xf', os.path.join(dest_dir, 'base.tar'), '-C', dest_basebackup]
                        self.log(untar)
                        subprocess.check_output(untar, stderr=subprocess.STDOUT)
                        os.remove(os.path.join(dest_dir, 'base.tar'))

                        for conf in ['recovery.conf', 'postgresql.conf', 'pg_hba.conf']:
                            shutil.copy(os.path.join(PSQL_CONF, conf), dest_basebackup)

                        for del_recreate in [pg_wal, pg_xlog, os.path.join(dest_basebackup, 'pg_log')]:
                            if os.path.isdir(del_recreate):
                                shutil.rmtree(del_recreate)
                            os.makedirs(del_recreate)

                        basebackup_found = True

                    # Move WAL (copy + del to set right owner on target)
                    if not os.path.exists(pg_xlog):
                        self.log('Unable to copy WAL, base directory not found %s' % pg_xlog)
                        continue
                    if not os.path.exists(oldwal):
                        self.log('Unable to copy WAL, wal directory not found %s' % oldwal)
                        continue

                    wal_moved = 0
                    forced_dump = forced_instance
                    for wal in os.listdir(full_name):
                        full_path_wal = os.path.join(full_name, wal)
                        if wal.endswith('7z') and not wal.startswith('.'):
                            try:
                                self.un7zip(full_path_wal, oldwal)
                                os.remove(full_path_wal)
                                wal_moved += 1
                            except subprocess.CalledProcessError as e:
                                # try to extract all WAL: UC when new bb generated to unlock a dump
                                self.error(e.output or e.stderr)
                            except Exception:
                                self.logger.exception('ERROR')

                        elif wal == 'force_dump':
                            os.remove(full_path_wal)
                            forced_dump = True

                    wal_not_dumped = os.path.join(dest_dir, 'wal_not_dumped')

                    if wal_moved:
                        self.log('%s, %d wal moved to %s' % (full_name, wal_moved, oldwal))
                    elif forced_dump:
                        self.log('%s, dump forced' % (full_name, ))
                    elif os.path.exists(wal_not_dumped):
                        last_wal_date = datetime.datetime.fromtimestamp(os.path.getmtime(wal_not_dumped))
                        if last_wal_date < datetime.datetime.now() - relativedelta(hours=36):
                            self.log('%s, wal_not_dumped forced' % (full_name, ))

                    if forced_dump or wal_moved or basebackup_found:
                        last_dump_file = os.path.join(dest_dir, 'last_dump.txt')
                        last_wal_date = False
                        if not forced_dump and not basebackup_found and os.path.exists(last_dump_file):
                            last_dump_date = datetime.datetime.fromtimestamp(os.path.getmtime(last_dump_file))
                            with open(last_dump_file) as last_desc:
                                last_wal_date = last_desc.read()
                            # only 1 dump per day
                            if last_dump_date.strftime('%Y-%m-%d') == time.strftime('%Y-%m-%d'):
                                self.log('%s already dumped today' % instance)
                                open(wal_not_dumped, 'w').close()
                                continue

                        try:
                            # Start psql
                            PSQL_DIR = config.psql9_dir
                            VERSION_FILE = os.path.join(dest_basebackup, 'PG_VERSION')
                            if os.patch.isfile(VERSION_FILE):
                                with open(VERSION_FILE, 'r') as ve:
                                    version = ve.read()
                                    if version.startswith('14'):
                                        PSQL_DIR = config.psql14_dir
                            self.log('%s, pg_version: %s'% (instance, PSQL_DIR))
                            psql_start = [os.path.join(PSQL_DIR, 'pg_ctl.exe'),'-o', '-p %s'%psql_port, '-D', to_win(dest_basebackup), '-t', '1200', '-w', 'start']
                            self.log(' '.join(psql_start))
                            subprocess.run(psql_start, check=True)
                            #subprocess.check_output(psql_start)

                            db = psycopg2.connect('dbname=template1 host=127.0.0.1 user=openpg port=%s'%psql_port)
                            cr = db.cursor()
                            # wait end of wall processing
                            previous_wall = False
                            while True:
                                cr.execute("SELECT pg_last_xlog_replay_location()")
                                prev = cr.fetchone()[0]
                                if prev == previous_wall:
                                    break
                                self.log('%s wait recovery, previous: %s, current: %s' % (instance, previous_wall, prev))
                                previous_wall = prev
                                #time.sleep(10)
                                time.sleep(60)

                            if not previous_wall:
                                self.error('%s no WAL replayed' % instance)

                            cr.execute("SELECT pg_last_xact_replay_timestamp()")
                            restore_date = cr.fetchone()[0]
                            if not restore_date:
                                cr.execute("select checkpoint_time from pg_control_checkpoint()")
                                check_point = cr.fetchone()
                                if check_point:
                                    restore_date = check_point[0]
                                    self.log('%s : get restore date from pg_control_checkpoint: %s' % (instance, restore_date.strftime('%Y%m%d-%H%M%S')))

                            if not restore_date:
                                self.error('%s no last replay timestamp' % instance)
                                label_file = os.path.join(dest_basebackup, 'backup_label.old')
                                if os.path.exists(label_file):
                                    restore_date = datetime.datetime.fromtimestamp(os.path.getmtime(label_file))

                            if not restore_date:
                                restore_date = datetime.datetime.now()

                            cr.execute('SELECT datname FROM pg_database')
                            all_dbs = cr.fetchall()
                            db.close()

                            if last_wal_date and last_wal_date == restore_date.strftime('%Y%m%d-%H%M%S'):
                                # same wal as previous dump: do noting (the in-progess wal is the 1st one)
                                self.log('%s : same data (%s) as previous backup (%s), do not dump/push to od' % (instance, last_wal_date, restore_date.strftime('%Y%m%d-%H%M%S')))
                                continue

                            # dump and zip the dump
                            for x in all_dbs:
                                try:
                                    final_zip = False
                                    dump_file = False
                                    if x[0] not in ['template0', 'template1', 'postgres']:
                                        self.log('%s db found %s'% (instance, x[0]))
                                        db = psycopg2.connect('dbname=%s host=127.0.0.1 user=openpg port=%s' % (x[0], psql_port))
                                        cr = db.cursor()
                                        cr.execute('SELECT name FROM sync_client_version where date is not null order by date desc limit 1')
                                        version = cr.fetchone()
                                        if not version:
                                            self.error('%s: version not found' % instance)
                                            version = 'XX'
                                        else:
                                            version = version[0]
                                        cr.execute('SELECT oc FROM sync_client_entity')
                                        oc = cr.fetchone()[0]
                                        if not oc:
                                            self.error('%s: OC not found' % instance)
                                            oc = 'XX'
                                        db.close()

                                        dump_file = os.path.join(DUMP_DIR, '%s-%s-C-%s.dump' % (x[0], restore_date.strftime('%Y%m%d-%H%M%S'), version))
                                        self.log('Dump %s' % dump_file)
                                        pg_dump = [os.path.join(PSQL_DIR, 'pg_dump.exe'), '-h', '127.0.0.1', '-p', psql_port, '-U', 'openpg', '-Fc', '--lock-wait-timeout=120000',  '-f', to_win(dump_file), x[0]]
                                        subprocess.check_output(pg_dump, stderr=subprocess.STDOUT)

                                        final_zip = os.path.join(DUMP_DIR, '%s-%s.zip' % (x[0], day_abr[datetime.datetime.now().weekday()]))
                                        if os.path.exists(final_zip):
                                            os.remove(final_zip)

                                        zip_c = ['zip', '-j', '-q', final_zip, dump_file]
                                        self.log(' '.join(zip_c))
                                        subprocess.call(zip_c)
                                        os.remove(dump_file)
                                        self.upload_od(final_zip, oc)
                                        with open(last_dump_file, 'w') as last_desc:
                                            last_desc.write(restore_date.strftime('%Y%m%d-%H%M%S'))
                                        if os.path.exists(wal_not_dumped):
                                            os.remove(wal_not_dumped)
                                except subprocess.CalledProcessError as e:
                                    self.error(e.output or e.stderr)
                                except Exception:
                                    self.logger.exception('ERROR')
                                finally:
                                    if dump_file and os.path.exists(dump_file):
                                        os.remove(dump_file)
                                    if final_zip and os.path.exists(final_zip):
                                        os.remove(final_zip)

                        finally:
                            psql_stop = [os.path.join(PSQL_DIR, 'pg_ctl.exe'), '-D', to_win(dest_basebackup), '-t', '1200', '-w', 'stop']
                            self.log(' '.join(psql_stop))
                            subprocess.run(psql_stop)

                thread_touch = '%s-%s' % (TOUCH_FILE_DUMP, self.thread)
                with open(thread_touch, 'w') as t_file:
                    t_file.write(time.strftime('%Y-%m-%d%H%M%S'))

            except subprocess.CalledProcessError as e:
                self.error(e.output or e.stderr)
            except Exception:
                self.logger.exception('ERROR')

if __name__ == '__main__':
    nb_threads = 3
    threads = []
    q = Queue()
    q.add('INIT')
    for x in range(0, nb_threads):
        t = threading.Thread(target=Process(x, q).process_directory)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    stopped(True)
    sys.exit(0)

