#! /bin/bash

TAG=""
#TAG="-r pilot1.3"
BZRBRANCH=""
#BZRBRANCH="/pilot"

if [ -z "$1" ]; then
    echo "$0 target_dir"
    exit 1
fi

if [ -f "$1" ]; then
    echo "Directory $1 exists"
    exit 1
fi

mkdir $1
cd $1

echo "== server =="
bzr branch $TAG lp:unifield-server${BZRBRANCH} unifield-server
cd unifield-server/bin/addons

echo "== addons =="
bzr branch $TAG lp:unifield-addons${BZRBRANCH} unifield-addons
mv unifield-addons/* .
rm -fr unifield-addons

echo "== wm =="
bzr branch $TAG lp:unifield-wm${BZRBRANCH} unifield-wm
mv unifield-wm/* .
rm -fr unifield-wm

echo "== sync_module =="
bzr branch $TAG lp:~unifield-team/unifield-wm/sync_module_prod
mv sync_module_prod/* .
rm -fr sync_module_prod
