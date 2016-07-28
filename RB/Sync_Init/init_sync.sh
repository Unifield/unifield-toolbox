#!/bin/bash
if [ "$1" == "--old" ]; then
        BRANCH_DEFAULT_SERVER="lp:unifield-server/old"
        BRANCH_DEFAULT_ADDONS="lp:unifield-addons"
        BRANCH_DEFAULT_WM="lp:unifield-wm"
        BRANCH_DEFAULT_SYNC="lp:unifield-wm/sync"
        REV="$2"
else
        BRANCH_DEFAULT_SERVER="lp:unifield-server"
        BRANCH_DEFAULT_ADDONS=""
        BRANCH_DEFAULT_WEB="lp:unifield-web"
        BRANCH_DEFAULT_WM=""
        BRANCH_DEFAULT_SYNC=""
        REV="$1"

fi

source ~/RBconfig

BRANCH_DEFAULT_WEB="lp:unifield-web"
BRANCH_DEFAULT_ENV="lp:~unifield-team/unifield-wm/sync-env"

[ -z "$REV" ] && echo "Please specify revision: dsp-utp141 for example" && exit 1
BRANCHES="branches/$REV"

if [ -f "$BRANCHES" ]; then
    . "$BRANCHES"
    correct=skip
else
    correct=no
fi

while ! [ $correct == "y" ]
do
    if ! [ "$correct" == "skip" ]; then
        echo -n "Enter server branch [$BRANCH_DEFAULT_SERVER]: "; read server
        [ -z "$server" ] && server=$BRANCH_DEFAULT_SERVER
        echo -n "Enter addons branch [$BRANCH_DEFAULT_ADDONS]: "; read addons
        [ -z "$addons" ] && addons=$BRANCH_DEFAULT_ADDONS
        echo -n "Enter web branch [$BRANCH_DEFAULT_WEB]: "; read web
        [ -z "$web" ] && web=$BRANCH_DEFAULT_WEB
        echo -n "Enter wm branch [$BRANCH_DEFAULT_WM]: "; read wm
        [ -z "$wm" ] && wm=$BRANCH_DEFAULT_WM
        echo -n "Enter sync branch [$BRANCH_DEFAULT_SYNC]: "; read sync
        [ -z "$sync" ] && sync=$BRANCH_DEFAULT_SYNC
        echo -n "Enter env branch [$BRANCH_DEFAULT_ENV]: "; read env
        [ -z "$env" ] && env=$BRANCH_DEFAULT_ENV
    fi
    echo "Please check the branches:"
    echo "+ Unifield Server: $server"
    echo "+ Unifield Addons: $addons"
    echo "+ Unifield Web: $web"
    echo "+ Unifield WM: $wm"
    echo "+ Unifield Sync: $sync"
    echo "+ Unifield Sync Env: $env"
    echo -n "=> Is it correct? [Y] "; read correct
    [ -z "$correct" ] && correct=y
done

echo "server=\"$server\"" > $BRANCHES
echo "addons=\"$addons\"" >> $BRANCHES
echo "web=\"$web\"" >> $BRANCHES
echo "wm=\"$wm\"" >> $BRANCHES
echo "sync=\"$sync\"" >> $BRANCHES
echo "env=\"$env\"" >> $BRANCHES


USERERP=${REV}
DBNAME="${REV}"
BZBRANCH=""
ADMINDBPASS=$web_db_pass

useradd -s /bin/bash -d /home/${USERERP} -m ${USERERP}
userid=`id -u ${USERERP}`

NETRPCPORT=${userid}1
WEBPORT=${userid}2
XMLRPCPORT=${userid}3
PGPORT=${userid}4

ADDONS=""
ADDONSDIR="'unifield-server', 'unifield-web'"
UNIFIELDTEST="/home/${USERERP}/unifield-server/bin/addons/unifield_tests/"

create_file() {
sed -e "s#@@USERERP@@#${USERERP}#g" \
    -e "s#@@DBNAME@@#${DBNAME}#g" \
    -e "s#@@XMLRPCPORT@@#${XMLRPCPORT}#g" \
    -e "s#@@NETRPCPORT@@#${NETRPCPORT}#g" \
    -e "s#@@PGPORT@@#${PGPORT}#g" \
    -e "s#@@ADMINDBPASS@@#${ADMINDBPASS}#g" \
    -e "s#@@URL@@#${URL}#g" \
    -e "s#@@ADDONS@@#${ADDONS}#g" \
    -e "s#@@RB_SERVER_URL@@#${rb_server_url}#g" \
    -e "s#@@CLOUD_BENCH_KEY@@#${CLOUD_BENCH_KEY}#g" \
    -e "s#@@USER_DUMP_SYNC@@#${user_dump_sync}#g" \
    -e "s#@@PASS_DUMP_SYNC@@#${pass_dump_sync}#g" \
    -e "s#@@UNIFIELDTEST@@#${UNIFIELDTEST}#g" \
    -e "s#@@WEB_ADMIN_PASS@@#${web_admin_pass}#g" \
    -e "s#@@WEB_LOGIN_USER@@#${web_login_user}#g" \
    -e "s#@@WEB_LOGIN_PASS@@#${web_login_pass}#g" \
    -e "s#@@NUM_PROJECT@@#${num_project}#g" \
    -e "s#@@ADDONSDIR@@#${ADDONSDIR}#g" \
    -e "s#@@WEBPORT@@#${WEBPORT}#g" $1  > $2
}


config_file() {
    create_file ./File/openerp-server-sprint1  /etc/init.d/${USERERP}-server
    create_file ./File/openerp-web-sprint1 /etc/init.d/${USERERP}-web
    create_file ./File/openerpallrc /home/${USERERP}/etc/openerprc
    create_file ./File/openerp-web.cfg /home/${USERERP}/etc/openerp-web.cfg
    create_file ./File/sync-envall.py /home/${USERERP}/sync_env_script/config.py
    create_file ./File/unifield.config /home/${USERERP}/unifield.config
    create_file ./File/bash_profile /home/${USERERP}/.bash_profile
    create_file ./File/apache.conf /etc/apache2/sites-enabled/${USERERP}
    create_file ./File/restore_dumprc /home/${USERERP}/.restore_dumprc
    create_file ./File/config.sh /home/${USERERP}/config.sh
    create_file ./File/build_and_test_all /home/${USERERP}/build_and_test.sh

    cp ./File/runtests.sh /home/${USERERP}/
    chmod +x /home/${USERERP}/build_and_test.sh
    chown ${USERERP}.${USERERP} /home/${USERERP}/etc/openerp-web.cfg /home/${USERERP}/etc/openerprc /home/${USERERP}/sync_env_script/config.py /home/${USERERP}/.bash_profile /home/${USERERP}/build_and_test.sh
    update-rc.d ${USERERP}-web defaults
    update-rc.d ${USERERP}-server defaults
    chmod +x /etc/init.d/${USERERP}-web /etc/init.d/${USERERP}-server
}

bzr_type=branch
init_user() {
    su - postgres -c -- "createuser -S -R -d ${USERERP}"
    cp -a  ${template_dir}/.bzr ${template_dir}/tmp /home/${USERERP}/
    chown -R ${USERERP}.${USERERP} /home/${USERERP}/.bzr /home/${USERERP}/tmp
    su - ${USERERP} <<EOF

[ -n "$wm" ] && bzr ${bzr_type} "${wm:=${BRANCH_DEFAULT_WM}}" unifield-wm
[ -n "$addons" ] && bzr ${bzr_type} "${addons:=${BRANCH_DEFAULT_ADDONS}}" unifield-addons
bzr ${bzr_type} "${web:=${BRANCH_DEFAULT_WEB}}" unifield-web
bzr ${bzr_type} "${server:=${BRANCH_DEFAULT_SERVER}}" unifield-server
[ -n "$sync" ] && bzr ${bzr_type} "${sync:=${BRANCH_DEFAULT_SYNC}}" sync_module_prod
bzr ${bzr_type} "${env:=${BRANCH_DEFAULT_ENV}}" sync_env_script

mkdir etc log exports
EOF
}

restart_servers() {
    echo "Start servers"
    /etc/init.d/${USERERP}-server start
    /etc/init.d/${USERERP}-web start
}

if [ -n "$wm" ]; then
    ADDONS="/home/${USERERP}/unifield-addons,/home/${USERERP}/unifield-wm,/home/${USERERP}/sync_module_prod"
    ADDONSDIR="'unifield-server', 'unifield-addons', 'unifield-wm', 'sync_module_prod', 'unifield-web'"
    UNIFIELDTEST="/home/${USERERP}/unifield-wm/unifield_tests/"
fi
init_user
config_file
restart_servers
/etc/init.d/apache2 reload

echo """Net-RPC port: $NETRPCPORT
XML-RPC port: $XMLRPCPORT
HTML port: $WEBPORT
URL: http://${USERERP}.${rb_server_url}
Testfield: http://${USERERP}_testfield.${rb_server_url}""" > /home/${USERERP}/RB_info.txt

cat /home/${USERERP}/RB_info.txt

echo "Please run ./mkdb.py as user $USERERP to finish:"
echo "su - $USERERP"
echo "cd ~/sync_env_script; python mkdb.py"
#echo "OR"
#echo "bash build_and_test.sh"
#echo "./mkdb.py ; cp /home/$USERERP/unifield.config /home/$USERERP/unifield-wm/unifield_tests/; cd /home/$USERERP/unifield-wm/unifield_tests/; python test_runner.py"

