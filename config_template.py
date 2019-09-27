# OneDrive
password=''
"""
path = {
   'oca': '/personal/UF_OCA_msf_geneva_msf_org/Documents/Backups/',
   'ocb': '/personal/UF_OCB_msf_geneva_msf_org/Documents/Backups/',
   'ocg': '/personal/UF_OCG_msf_geneva_msf_org/Documents/Backups/',
   'ocp': '/personal/UF_OCP_msf_geneva_msf_org/Documents/Backups/',
}
"""
path = {
    'oca': '/personal/UF_OCA_msf_geneva_msf_org/documents/Test',
    'ocb': '/personal/UF_OCB_msf_geneva_msf_org/documents/Test',
    'ocg': '/personal/UF_OCG_msf_geneva_msf_org/documents/Test',
    'ocp': '/personal/UF_OCP_msf_geneva_msf_org/documents/Test',
}

# path to psql exe
psql_dir = '/cygdrive/c/WalTools/pgsql/bin/'

# path to destination base + Wal
dest_dir = '/cygdrive/d/continuous_backup_data'

# path to instance push
src_dir = '/home/backup/'

log_file = '/cygdrive/c/continuous_backup_server/creator.log'

# key files
# storage
keys_dir = '/cygdrive/d/continuous_backup_data/ssh_keys'
smtp_host = '80.12.95.139'
from_mail = ''
to_mail = ''
