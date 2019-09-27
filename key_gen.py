#!./crypto-env/bin/python3
from Crypto.PublicKey import RSA
import sys
import zipfile
import os
from email.message import EmailMessage
import smtplib
import config

authorized_keys = os.path.join(config.src_dir, '.ssh', 'authorized_keys')
keys_dir = config.keys_dir
smtp_host = config.smtp_host

if not sys.argv or len(sys.argv) != 2:
    print('%s instance' % sys.argv[0])
    sys.exit(1)

instance = sys.argv[1]
auth_read = open(authorized_keys, 'r')
line = 0
for x in auth_read:
    line += 1
    if x.strip().endswith(instance):
        print ('%s found in authorized_keys, line %s' % (instance, line))
        sys.exit(1)
auth_read.close()

if not os.path.exists(keys_dir):
    os.makedirs(keys_dir)
zip_file = os.path.join(keys_dir, '%s.zip'%instance)

if os.path.exists(zip_file):
    print('%s already exists'  % (zip_file, ))
    sys.exit(1)

zip_desc = open(zip_file, 'wb')
zip_doc = zipfile.ZipFile(zip_desc, mode='w', compression=zipfile.ZIP_DEFLATED)

key = RSA.generate(1024)
zip_doc.writestr('SSH_CONFIG/id_rsa', key.exportKey('PEM'))

pubkey = key.publickey()
exported_pub_key = pubkey.exportKey('OpenSSH')
zip_doc.writestr('SSH_CONFIG/id_rsa.pub', exported_pub_key)


zip_doc.writestr('SSH_CONFIG/config', """
IdentityFile "C:\Program Files (x86)\msf\SSH_CONFIG\id_rsa"
StrictHostKeyChecking no
UserKnownHostsFile "C:\Program Files (x86)\msf\SSH_CONFIG\knownhosts"
""")
zip_doc.close()
zip_desc.close()

auth = open(authorized_keys, 'ab')
b_instance =  bytes(instance, 'utf-8')
auth.write(b'### %s\n' % b_instance)
auth.write(b'command="rsync --server -vlogDtr --no-perms --chmod=Dg+rwx,Fg+rw --remove-source-files --partial-dir=.rsync-partial --partial . %s/",no-agent-forwarding,no-port-forwarding,no-pty,no-user-rc,no-X11-forwarding %s %s\n' % (b_instance, exported_pub_key, b_instance))
auth.close()

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
msg.add_attachment(data, maintype='application', subtype='zip', filename='ssh_config.zip')
# Send the email via our own SMTP server.
with smtplib.SMTP(smtp_host) as s:
    s.send_message(msg)

