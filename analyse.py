#!/usr/bin/python3.6

import os
import subprocess
import datetime
from dateutil.relativedelta import relativedelta
import sys
import config
import zipfile
import re
from termcolor import colored
import shutil

PSQL_DIR = config.psql_dir
DEST_DIR = config.dest_dir
SRC_DIR = config.src_dir
DUMP_DIR = os.path.join(DEST_DIR, 'DUMPS')
LOG_FILE = config.log_file
KEYS = config.keys_dir
day_abr = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


LOG_FILES_TO_CHECK = ['%s.%s' % (LOG_FILE, (datetime.datetime.now() + relativedelta(days=-1)).strftime('%Y-%m-%d')), LOG_FILE]


# Get all ssh keys
keys_date = {}
for key in os.listdir(KEYS):
    if key.endswith('.zip'):
        keys_date[key.split('.')[0]] = datetime.datetime.fromtimestamp(os.path.getctime(os.path.join(KEYS, key)))

all_keys = sorted(keys_date.keys())
print('%d keys' % (len(all_keys)))

print('== Errors ==')
subprocess.call(['grep', '-h', 'ERROR']+LOG_FILES_TO_CHECK)

print("== New BB ==")
subprocess.call(['grep', '-h', 'backup.7z']+LOG_FILES_TO_CHECK)

# Extract info from DUMP.zip
zip_dump_details = {}
dump_details = {}
for dump in os.listdir(DUMP_DIR):
    full_dump = os.path.join(DUMP_DIR, dump)
    full_dump_date = datetime.datetime.fromtimestamp(os.path.getctime(full_dump))
    instance_name = dump[0:-8].lower()
    dump_details.setdefault(full_dump_date.strftime('%Y-%m-%d'), []).append(instance_name)
    if zipfile.is_zipfile(full_dump):
        zip_data = zipfile.ZipFile(full_dump, mode='r')
        for zipname in zip_data.namelist():
            m = re.search('^[a-z0-9_-]+-([0-9]{8}-[0-9]{6})', zipname, re.I)
            if m:
                zip_dump_details.setdefault(instance_name, []).append(m.group(1))
        zip_data.close()

print("== Dumps ==")
max_dump_date = (datetime.datetime.now() + relativedelta(days=-7)).strftime('%Y-%m-%d')
for d in sorted(dump_details.keys(), reverse=True):
    if max_dump_date < d:
        missing = list(set([x for x in keys_date if keys_date[x].strftime('%Y-%m-%d') <= d])-set(dump_details[d]))
        missing_list = ''
        if d != datetime.datetime.now().strftime('%Y-%m-%d'):
            missing_list = ', '.join(sorted(missing))
        print('%s: %d dumps, %d missing: %s' % (d, len(dump_details[d]), len(missing), missing_list))


# Extract info from last_dump.txt generated after an pg_dump
print("== Last Dump ==")
days_2 = (datetime.datetime.now() + relativedelta(days=-2)).strftime('%Y-%m-%d')
last_dump = {}
for x in all_keys:
    dump_file = os.path.join(DEST_DIR, x, 'last_dump.txt')
    wal_date = "00000000-000000"
    all_dump = []
    if os.path.exists(dump_file):
        last = datetime.datetime.fromtimestamp(os.path.getctime(dump_file)).strftime('%Y-%m-%d %H:%M')
        with open(dump_file) as last_desc:
            wal_date = last_desc.read() or wal_date
    else:
        last = '0000-00-00 00:00'
    if zip_dump_details.get(x):
        zip_dump_details[x].sort(reverse=1)
        for idx in range(0, 7):
            if len(zip_dump_details[x]) > idx:
                zip_date = zip_dump_details[x][idx]
                if idx > 0 and zip_date == zip_dump_details[x][idx-1]:
                    zip_date = colored(zip_date, 'red')
                all_dump.append(zip_date)
    last_dump.setdefault(last, []).append((x, wal_date, all_dump))

print("inst\t\tpush date\t\tlast wal\tdate from zip")
for d in sorted(last_dump.keys(), reverse=True):
    last = d
    if last <= days_2:
        last = colored(last, 'red')
    for instance in sorted(last_dump[d]):
        print("%s\t%s\t%s\t%s" % (instance[0], last, instance[1], "\t".join(instance[2])))


total, used, free = shutil.disk_usage("/")
print("== Disk ==\nDisk used %s GB on %s GB (%.02lf%%)" % (used // (2**30), total // (2**30), used/total*100))
sys.exit(1)

