#!/usr/bin/python3.6

import os
import subprocess
import datetime
from dateutil.relativedelta import relativedelta
import sys
import config
#import zipfile

PSQL_DIR = config.psql_dir
DEST_DIR = config.dest_dir
SRC_DIR = config.src_dir
DUMP_DIR = os.path.join(DEST_DIR, 'DUMPS')
LOG_FILE = config.log_file
KEYS = config.keys_dir
day_abr = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


LOG_FILES_TO_CHECK = [LOG_FILE, '%s.%s' % (LOG_FILE, (datetime.datetime.now() + relativedelta(days=-1)).strftime('%Y-%m-%d'))]

#subprocess.check_output(command, stderr=subprocess.STDOUT)

all_keys = []
for key in os.listdir(KEYS):
    if key.endswith('.zip'):
        all_keys.append(key.split('.')[0])

all_keys.sort()
print('%d keys' % (len(all_keys)))

print('== Errors ==')
subprocess.call(['grep', '-h', 'ERROR']+LOG_FILES_TO_CHECK)

print("== New BB ==")
subprocess.call(['grep', '-h', 'backup.7z']+LOG_FILES_TO_CHECK)


dump_details = {}
for dump in os.listdir(DUMP_DIR):
    full_dump = os.path.join(DUMP_DIR, dump)
    full_dump_date = datetime.datetime.fromtimestamp(os.path.getctime(full_dump))
    dump_details.setdefault(full_dump_date.strftime('%Y-%m-%d'), []).append(dump[0:-8].lower())
    #zip_data = zipfile.ZipFile(full_dump, mode='r')
    #print(zip_data.namelist())
    #zip_data.close()

print("== Dumps ==")
max_dump_date = (datetime.datetime.now() + relativedelta(days=-7)).strftime('%Y-%m-%d')
for d in sorted(dump_details.keys(), reverse=True):
    if max_dump_date < d:
        missing = list(set(all_keys)-set(dump_details[d]))
        missing_list = ''
        if d != datetime.datetime.now().strftime('%Y-%m-%d'):
            missing_list = ', '.join(sorted(missing))
        print('%s: %d dumps, %d missing: %s' % (d, len(dump_details[d]), len(missing), missing_list))


print("== Last Dump ==")
days_2 = (datetime.datetime.now() + relativedelta(days=-2)).strftime('%Y-%m-%d')
last_dump = {}
for x in all_keys:
    dump_file = os.path.join(DEST_DIR, x, 'last_dump.txt')
    wal_date = False
    if os.path.exists(dump_file):
        last = datetime.datetime.fromtimestamp(os.path.getctime(dump_file)).strftime('%Y-%m-%d %H:%M')
        with open(dump_file) as last_desc:
            wal_date = last_desc.read()
    else:
        last = '0000-00-00 00:00'
    last_dump.setdefault(last, []).append((x, wal_date))

for d in sorted(last_dump.keys(), reverse=True):
    last = d
    if last <= days_2:
        last+='*'
    for instance in sorted(last_dump[d]):
        print("%s\t%s\t%s" % (instance[0], last, instance[1]))

sys.exit(1)

