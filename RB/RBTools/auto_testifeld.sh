#! /bin/bash

# script to start testfield on existing user
# for example add this in /etc/crontab
# 30  22 * * *  jfb-auto /opt/unifield-toolbox/RB/RBTools/auto_testfield.sh lp:unifield-server lp:unifield-web
# RB env for jfb-auto must exist

if [[ $# -ne 2 ]]; then
   echo "$0 <server branch> <web branch>"
   exit 0
fi

my_user=`id -nu`
cd /home/${my_user}
export USER=${my_user}
export PATH=/usr/local/bin:/usr/bin:/bin:/usr/local/games:/usr/games

./runtests.sh test $(date +"%Y-%m-%d-%H%M") $1 $2
