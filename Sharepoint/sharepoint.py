#!/bin/env python3
import webdav
import configparser
import requests
import sys
from urllib.parse import urlparse
import os
import time
import re

# OCB
# "https://msfintl-my.sharepoint.com/personal/UF_OCB_msf_geneva_msf_org/Documents/Backups"
# "https://msfintl-my.sharepoint.com/personal/UF_OCB_msf_geneva_msf_org/Documents/Decommissioned instances(last dump) -Archive"

# OCA
# "https://msfintl-my.sharepoint.com/personal/UF_OCA_msf_geneva_msf_org/Documents/Backups"
# "https://msfintl-my.sharepoint.com/personal/UF_OCA_msf_geneva_msf_org/Documents/Decommissioned Instances"

# OCP
# "https://msfintl-my.sharepoint.com/personal/UF_OCP_msf_geneva_msf_org/Documents/Backups"
# "https://msfintl-my.sharepoint.com/personal/UF_OCP_msf_geneva_msf_org/Documents/Decommissioned Instance last dumps"


rcfile = '~/.restore_dumprc'
cfile = os.path.realpath(os.path.expanduser(rcfile))
username = False
password = False

url_shortcut = {
    'oca': 'https://msfintl-my.sharepoint.com/personal/UF_OCA_msf_geneva_msf_org/Documents/Backups',
    'oca_decom': 'https://msfintl-my.sharepoint.com/personal/UF_OCA_msf_geneva_msf_org/Documents/Decommissioned Instances',
    'ocb': 'https://msfintl-my.sharepoint.com/personal/UF_OCB_msf_geneva_msf_org/Documents/Backups',
    'ocb_decom': 'https://msfintl-my.sharepoint.com/personal/UF_OCB_msf_geneva_msf_org/Documents/Decommissioned instances(last dump) -Archive',
    'ocp': 'https://msfintl-my.sharepoint.com/personal/UF_OCP_msf_geneva_msf_org/Documents/Backups',
    'ocp_decom': 'https://msfintl-my.sharepoint.com/personal/UF_OCP_msf_geneva_msf_org/Documents/Decommissioned Instance last dumps',
    'ocg': 'https://msfintl-my.sharepoint.com/personal/UF_OCG_msf_geneva_msf_org/Documents/Backups',
    'ocg_decom': 'https://msfintl-my.sharepoint.com/personal/uf_ocg_msf_geneva_msf_org/Documents/Decommissioned%20Instances%20-Archive'
}

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
    url = url_shortcut.get(url, url)
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
    list_file = []
    for f in dav.list(dav_data['path']):
        if not pattern or pattern and re.search(pattern, f['Name']):
            list_file.append((f['Name'], f.get('TimeLastModified')))
    return list_file

def delete_f(share_pointurl):
    parsed_url = urlparse(clean_url(share_pointurl))
    filename = os.path.basename(parsed_url.path)
    dirname = os.path.dirname(parsed_url.path)
    dav_data.update({
        'host': parsed_url.netloc,
        'path': dirname,
    })
    dav = webdav.Client(**dav_data)
    dav.delete(filename)

def delete_pattern(share_pointurl, pattern):
    l = list_f(share_pointurl, pattern)
    for x in l:
        print(x[0], x[1])
    ret = input('Delete ? y/n ')
    if ret == 'y':
        parsed_url = urlparse(clean_url(share_pointurl))
        dav_data.update({
            'host': parsed_url.netloc,
            'path': parsed_url.path,
        })
        dav = webdav.Client(**dav_data)
        for x in l:
            dav.delete(x[0])

def help():
    print("""%s
        get remote_url [locale_dir]
        push local_file remote_url
        list remote_url [pattern]
        delete remote_url [pattern]
    """ % (sys.argv[0], ))

    print('remote_url shortcuts: %s' % (', '.join(url_shortcut.keys())))
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
    for x in list_f(sys.argv[2], pattern):
        print(x[0], x[1])
elif sys.argv[1] == 'delete':
    pattern = None
    if len(sys.argv) > 3:
        delete_pattern(sys.argv[2], sys.argv[3])
    else:
        delete_f(sys.argv[2])
else:
    help()
