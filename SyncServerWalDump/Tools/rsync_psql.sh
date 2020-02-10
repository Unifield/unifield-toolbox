date
#rsync --delete -a root@212.95.73.128:/var/lib/postgresql/10/main /opt/SYNC/sync_prod
rm /opt/SYNC/sync_prod/main/postmaster.pid
date
rsync -a root@212.95.73.128:/opt/WAL/ /opt/SYNC/WAL/
chown -R psqlsync /opt/SYNC/WAL
date
