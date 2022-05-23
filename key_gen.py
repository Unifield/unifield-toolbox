#!/cygdrive/c/continuous_backup_server/crypto-env/bin/python3.6
from Crypto.PublicKey import RSA
import sys
import zipfile
import os
from email.message import EmailMessage
import smtplib
import config
import re

authorized_keys = os.path.join(config.src_dir, '.ssh', 'authorized_keys')
keys_dir = config.keys_dir
smtp_host = config.smtp_host

def error(msg):
    print(msg)
    input('Press enter to quit')
    sys.exit(1)

def sendemail(zip_file):
    # Create the container email message.
    msg = EmailMessage()
    msg['Subject'] = 'SSH Key %s' % instance
    # me == the sender's email address
    # family = the list of all recipients' email addresses
    msg['From'] = config.from_mail
    msg['To'] = config.to_mail
    msg.preamble = 'Key in attach'

    # Open the files in binary mode.  Use imghdr to figure out the
    # MIME subtype for each specific image.
    with open(zip_file, 'rb') as fp:
        data = fp.read()
    msg.add_attachment(data, maintype='application', subtype='zip', filename='%s.zip' % instance)
    # Send the email via our own SMTP server.
    with smtplib.SMTP(smtp_host) as s:
        s.send_message(msg)


if sys.argv and len(sys.argv) == 2:
    instance_input = sys.argv[1]
    ok = 'y'
else:
    ok = 'n'
    print("\n\n\n")

while ok not in ('Y', 'y'):
    if ok in ('n', 'N'):
        instance_input = input("Intance name: ")
    if ok in ('q', 'Q'):
        sys.exit(1)
    ok = input("'%s' do you confirm ? [y/n/q] " % instance_input)

instance = instance_input.lower().strip()
if not re.search('^[a-z0-9_-]+$', instance):
    error("Name '%s' is not correct" % instance_input)
    sys.exit(1)

zip_file = os.path.join(keys_dir, '%s.zip'%instance)

auth_read = open(authorized_keys, 'r')
line = 0
for x in auth_read:
    line += 1
    if x.strip().endswith(instance):
        if os.path.exists(zip_file):
            auth_read.close()
            sendemail(zip_file)
            sys.exit(0)
        error('%s found in authorized_keys, line %s' % (instance, line))
        sys.exit(1)
auth_read.close()

if not os.path.exists(keys_dir):
    os.makedirs(keys_dir)

if os.path.exists(zip_file):
    error('%s already exists'  % (zip_file, ))
    sys.exit(1)

zip_desc = open(zip_file, 'wb')
zip_doc = zipfile.ZipFile(zip_desc, mode='w', compression=zipfile.ZIP_DEFLATED)

key = RSA.generate(1024)
zip_doc.writestr('SSH_CONFIG/id_rsa', key.exportKey('PEM'))

pubkey = key.publickey()
exported_pub_key = pubkey.exportKey('OpenSSH')
zip_doc.writestr('SSH_CONFIG/id_rsa.pub', exported_pub_key)


b_instance =  bytes(instance, 'utf-8')
zip_doc.writestr('SSH_CONFIG/config', """
# %s
IdentityFile "C:\Program Files (x86)\msf\SSH_CONFIG\id_rsa"
StrictHostKeyChecking no
UserKnownHostsFile "C:\Program Files (x86)\msf\SSH_CONFIG\knownhosts"

# comment to use ssh on port 22
Port 8069
""" % (instance, ))
zip_doc.close()
zip_desc.close()

auth = open(authorized_keys, 'ab')
auth.write(b'### %s\n' % b_instance)
auth.write(b'command="rsync --server -vlogDtr --no-perms --chmod=Dg+rwx,Fg+rw --remove-source-files --partial-dir=.rsync-partial --partial . %s/",no-agent-forwarding,no-port-forwarding,no-pty,no-user-rc,no-X11-forwarding %s %s\n' % (b_instance, exported_pub_key, b_instance))
auth.close()
sendemail(zip_file)

