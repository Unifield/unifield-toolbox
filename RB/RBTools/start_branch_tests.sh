#! /bin/bash

# script to start devtest and testfield on given server and dev branches

if [[ $# -ne 3 ]]; then
   echo "$0 <server branch> <web branch> <rb prefix>"
   exit 0
fi

/root/RBTools/deleteRB.sh ${3}-d
/root/RBTools/deleteRB.sh ${3}-s
/root/Sync_Init/init_sync.sh -s $1 -w $2 -t devtests ${3}-d &
/root/Sync_Init/init_sync.sh -s $1 -w $2 -t testfield ${3}-s &
