#!/bin/env python3
import webdav
import configparser
import requests
import sys
from urllib.parse import urlparse
import os
import time
import re

rcfile = '~/.restore_dumprc'
cfile = os.path.realpath(os.path.expanduser(rcfile))
username = False
password = False
if os.path.exists(cfile):
    config = configparser.ConfigParser(interpolation=None)
    config.read([cfile])
    username = config.get('Sharepoint', 'username', fallback=None)
    password = config.get('Sharepoint', 'password', fallback=None)


if not username or not password:
    print('Set [Sharepoint] username and password in %s' % (cfile,))
    sys.exit(1)

dav_data = {
    'port': 443,
    'protocol': 'https',
    'username': username,
    'password': password,
}

max_retries = 3
buffer_size = 10 * 1024 * 1014

def clean_url(url):
    for x in  [':/r', '/:f', ':/e', '/:u']:
        url = url.replace(x, '')
    return url

def push(filename, share_pointurl):

    fileobj = open(filename, 'rb')
    filename = os.path.basename(filename)
    dav_connected = False
    retries = 0

    parsed_url = urlparse(clean_url(share_pointurl))
    dav_data.update({
        'host': parsed_url.netloc,
        'path': parsed_url.path,
    })
    while True:
        try:
            if not dav_connected:
                dav = webdav.Client(**dav_data)
                dav_connected = True

            upload_ok, dav_error = dav.upload(fileobj, filename, buffer_size=buffer_size, continuation=True)
            if upload_ok:
                print('Push done')
                break

            if retries > max_retries:
                raise Exception(dav_error)
            retries += 1
            time.sleep(2)
            if dav_connected and 'timed out' in dav_error or '2130575252' in dav_error:
                dav.login()
        except (requests.exceptions.RequestException, webdav.ConnectionFailed):
            if retries > max_retries:
                raise
            retries += 1
            time.sleep(2)
    fileobj.close()

def get(share_pointurl, local_dir):
    parsed_url = urlparse(clean_url(share_pointurl))
    filename = os.path.basename(parsed_url.path)
    dirname = os.path.dirname(parsed_url.path)
    dav_data.update({
        'host': parsed_url.netloc,
        'path': dirname,
    })
    dav = webdav.Client(**dav_data)

    local_file = os.path.join(local_dir, filename)
    dav.download(filename, local_file)
    print('Pull done: %s' % (local_file,))

def list_f(share_pointurl, pattern):
    parsed_url = urlparse(clean_url(share_pointurl))
    dav_data.update({
        'host': parsed_url.netloc,
        'path': parsed_url.path,
    })
    dav = webdav.Client(**dav_data)
    for f in dav.list(dav_data['path']):
        if not pattern or pattern and re.search(pattern, f['Name']):
            print(f['Name'], f.get('TimeLastModified'))

def help():
    print("""%s
        get remote_url [locale_dir]
        push local_file remote_url
        list remote_url [pattern]
    """ % (sys.argv[0], ))
    sys.exit(1)

if len(sys.argv) < 3:
    help()

if sys.argv[1] == 'push':
    if len(sys.argv) < 4:
        help()
    push(sys.argv[2], sys.argv[3])
elif sys.argv[1] == 'get':
    if len(sys.argv) < 4:
        locate_dir = '.'
    else:
        locate_dir = sys.argv[3]
    get(sys.argv[2], locate_dir)
elif sys.argv[1] == 'list':
    pattern = None
    if len(sys.argv) > 3:
        pattern = sys.argv[3]
    list_f(sys.argv[2], pattern)
else:
    help()
