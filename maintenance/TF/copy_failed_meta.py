#!/bin/env python3

from bs4 import BeautifulSoup
import requests
import sys
import os
import shutil

if len(sys.argv) < 1:
    print('%s <url> [src] [destination]' % sys.argv[0])
    sys.exit(1)
url = sys.argv[1]

if len(sys.argv) >= 3:
    src = sys.argv[2]
else:
    src = '/home/testing/testfield/meta_features'

if len(sys.argv) == 4:
    dest = sys.argv[3]
else:
    dest = 'meta_features'

if not os.path.exists(src):
    print('Source %s directory does not exist' % src)
    sys.exit(1)

if os.path.exists(dest):
    print('Destination %s directory exists' % dest)
    sys.exit(1)

r = requests.get(url)
soup = BeautifulSoup(r.text, 'html.parser')
for danger in soup.find_all('tr', class_='danger'):
    for p in danger.find_all('p', class_='text-muted'):
        dest_path = os.path.join(dest, os.path.dirname(p.text))
        os.makedirs(dest_path, exist_ok=True)
        shutil.copy(os.path.join(src, p.text), dest_path)
        print('Copy %s to %s' % (os.path.join(src, p.text), dest_path))
