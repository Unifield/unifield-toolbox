#!/usr/bin/env python

import sys
import os
import zipfile
import time
import re
import filecmp

if len(sys.argv) != 4:
    print 'Expected 3 arguments: <from_tree> <to_tree> <patch_zip_name>'
    sys.exit()

# Skip things that do not belong in patch files.
def should_skip(name):
    return (name.endswith('.pyc') or
            name in [
                # this will be added at the end of this script instead
                'release.py',
                # these are related to the AIO and should not go in the patch
                'Uninstall.exe',
                'web/Uninstall.exe',
                'setup.py',
                'setup_py2exe_custom.py',
                # these config files on the end-user installs should never
                # be overwritten
                'openerp-server.conf',
                'web/conf/openerp-web-oc.cfg',
    ])

# Change the directory from the filesystem into a destination directory in
# the patchfile (this mapping was set by the implementation of
# updater.py)

def dirmap(directory):
    directory = directory.replace(sys.argv[2], '')
    if directory.startswith('/'):
        directory = directory[1:]
    # unpdater.py expects lower case
    if directory.startswith('Web'):
        directory = 'w' + directory[1:]
    # change directory Server/foo to foo
    if directory == 'Server':
        directory = ''
    elif directory.startswith('Server/'):
        directory = directory[7:]
    return directory

# The plan:
#
# for each file in the original distribution:
#   remember it's name
#   if not in new distribution:
#     add to delete list
#   else
#     if new distribution version is different:
#       add to patch file
# for each file in the new distribution:
#   if we did not already see it:
#     add to patch file

deleted = []
seen = {}

old = sys.argv[1]
new = sys.argv[2]
zf = zipfile.ZipFile(sys.argv[3], mode='w', compression=zipfile.ZIP_DEFLATED)

for (dirpath, dirnames, filenames) in os.walk(old):
    relpath = dirpath.replace(old, '')
    if len(relpath) > 0 and relpath[0] == '/':
        relpath = relpath[1:]
    if relpath == 'ServerLog':
        continue
    for f in filenames:
        oldf = os.path.join(dirpath, f)
        newf = os.path.join(new, relpath, f)
        dest = os.path.join(dirmap(relpath), f)
        if should_skip(dest):
            continue
        if not os.path.exists(newf):
            print "del %s" % dest
            deleted.append(dest)
        elif not filecmp.cmp(oldf, newf, False):
            print "write mod %s" % dest
            zf.write(newf, dest)
        seen[dest] = True

for (dirpath, dirnames, filenames) in os.walk(new):
    relpath = dirpath.replace(new, '')
    if len(relpath) > 0 and relpath[0] == '/':
        relpath = relpath[1:]
    if relpath == 'ServerLog':
        continue
    for f in filenames:
        newf = os.path.join(new, relpath, f)
        dest = os.path.join(dirmap(relpath), f)
        if should_skip(dest) or dest in seen:
            continue
        print "write add %s" % dest
        zf.write(newf, dest)
        
# special case for release.py: add the date onto the end of the
# given version
with open(os.path.join(new, 'Server', 'release.py')) as f:
    lines = f.readlines()
out = []
for line in lines:
    if line.startswith('version = '):
        exec(line)
    else:
        out += line
                            
if not re.match('.*-[0-9]{8}-[0-9]{6}$', version):
    version += time.strftime('-%Y%m%d-%H%M%S')
    print "Version inserted into the patch is: %s" % version
else:
    print "Version in the source is already timestamped: %s" % version

out += 'version = \'%s\'\n' % version
zf.writestr('release.py', ''.join(out))

zf.writestr('delete.txt', '\n'.join(deleted))
zf.close()

