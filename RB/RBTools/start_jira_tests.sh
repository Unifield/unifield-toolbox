#! /bin/bash

# script to start testfield and dev test on jira ticket

if [[ $# -ne 2 ]]; then
   echo "$0 <jira ticket> <rb prefix>"
   exit 0
fi
TICKET=$1
PREF_DEV=${2}-d
PREF_SEL=${2}-s

/root/RBTools/deleteRB.sh ${PREF_DEV}-${TICKET}
/root/RBTools/deleteRB.sh ${PREF_SEL}-${TICKET}

/root/Sync_Init/init_sync.sh -jp ${PREF_DEV} -t devtests ${TICKET} &
/root/Sync_Init/init_sync.sh -jp ${PREF_SEL} -t testfield ${TICKET} &
