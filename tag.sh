#! /bin/bash

if [ -z "$1" ]; then
    echo "$0 <tag>"
    exit 0
fi

mkdir $1
cd $1
for i in wm addons server web; do
    echo "################# $i #################"
    bzr branch lp:unifield-$i
    cd unifield-$i
    bzr tag $1
    bzr push lp:unifield-$i
    bzr push lp:unifield-$i/pilot
    cd -
done

for br in unifield-data sync_module_prod; do
    echo "################# $br #################"
    bzr  branch lp:~unifield-team/unifield-wm/${br}
    cd ${br}
    bzr tag $1
    bzr push lp:~unifield-team/unifield-wm/${br}
    cd -
done

