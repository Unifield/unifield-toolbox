#!/bin/sh

if [ "$#" -ne 1 ]; then
    echo "Illegal number of parameters";
    exit 1;
fi

TICKET_NAME=$1
UNIFIELDDIR=/home/qt/Development/Unifield

TICKET_DIR=$UNIFIELDDIR/branches/$TICKET_NAME

export PGHOST=`/home/qt/.myscripts/docker-ip unifield`
export PGUSER=docker
export PGPORT=5432
export PGPASSWORD=docker

# Create ticket dir
if [ ! -d "$TICKER_DIR" ]; then
    echo "Download branch..."
    bzr branch lp:~unifield-team/unifield-server/$TICKET_NAME $TICKET_DIR
    if [ "$?" != "0" ]; then
        bzr branch lp:unifield-server $TICKET_DIR
        echo "Branch downloaded from lp:unifield-server"
    else
        echo "Branch downloaded from lp:~unifield-team/unifield-server/$TICKET_NAME"
    fi
    cd $TICKET_DIR
    bzr push lp:~unifield-team/unifield-server/$TICKET_NAME
fi

# Create dumps directory
DUMP_DIR=$UNIFIELDDIR/dumps
if [ ! -d "$DUMP_DIR" ]; then
    mkdir $DUMP_DIR;
fi

# Get dump from uf3
today=$(date +%Y%m%d)
for i in HQ1 HQ1C1 HQ1C1P1 SYNC_SERVER; do
    echo "Manage $i database"
    PGDATABASE=$TICKET_NAME'_'$i
    SYNCSERVERDB=$TICKET_NAME'_SYNC_SERVER'
    scp -r root@uf0003.unifield.org:/home/se-qt/exports/last/se-qt_$i.dump $UNIFIELDDIR/dumps/$PGDATABASE.dump
    createdb $PGDATABASE
    pg_restore -d $PGDATABASE < $UNIFIELDDIR/dumps/$PGDATABASE.dump
    psql $PGDATABASE -c "UPDATE sync_client_sync_server_connection SET database = '$SYNCSERVERDB', host = 'localhost', port=8070;"
done

echo "Update SYNC_SERVER hardware_id"
psql -d $TICKET_NAME'_SYNC_SERVER' -c "UPDATE sync_server_entity SET hardware_id = '7abd3182d399f7bdda199550d8babede';"

unset PGHOST
unset PGUSER
unset PGPORT
unset PGPASSWORD

echo "Done !"
