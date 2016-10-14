#!/bin/bash

end_of_script() {
    if [[ $? -ne 0 ]]; then
        STATUS='FAILED'
    else
        STATUS='OK'
    fi
    send_mail $STATUS
}
send_mail() {
    TMPFILE=/tmp/mkdb$$
    cat /home/$USERERP/RB_info.txt > $TMPFILE
    echo >> $TMPFILE
    echo >> $TMPFILE
    echo "---------------" >> $TMPFILE
    cat $LOGFILE >> $TMPFILE
    mail -s "RB ${REV} ${1}" $MAILTO < $TMPFILE
    rm -f $TMPFILE
}
BRANCH_DEFAULT_SERVER="lp:unifield-server"
BRANCH_DEFAULT_WEB="lp:unifield-web"
BRANCH_DEFAULT_ENV="lp:~unifield-team/unifield-wm/sync-env"
if [[ -f ~/RBconfig ]]; then
    source ~/RBconfig
fi

AUTO=
TESTFIELD=
DEVTEST=
MKDB_LANG="False"
MKDB_CURR='eur'
num_hq=1
num_coordo=1
INIT_ONLY=
COMMENT_ACL='"""'
FULL_TREE='"""'
while getopts i:s:w:m:l:c:atdhnuf opt; do
case $opt in
    f)
        AUTO=1
        FULL_TREE=
        ;;
    u)
        AUTO=1
        COMMENT_ACL=
        ;;
    s)
        server=$OPTARG
        AUTO=1
        ;;
    w)
        web=$OPTARG
        AUTO=1
        ;;
    m)
        env=$OPTARG
        AUTO=1
        ;;
    l)
        if [[ "$OPTARG" != "es" && "$OPTARG" != "fr" ]]; then
            echo "-l option should be en or fr not $MKDB_LANG"
            exit 1
        fi
        MKDB_LANG="'${OPTARG}_MF'"
        AUTO=1
        ;;
    c)
        MKDB_CURR=$OPTARG
        if [[ "$MKDB_CURR" != "eur" && "$MKDB_CURR" != "chf" ]]; then
            echo "-c option should be eur or chf not $MKDB_CURR"
            exit 1
        fi
        AUTO=1
        ;;
    a)
        AUTO=1
        ;;
    t)
        TESTFIELD=1
        ;;
    d)
        DEVTEST=1
        NUM_PROJECT=2
        ;;
    i)
        AUTO=1
        IFS="-"
        arr=($OPTARG)
        unset IFS
        num_hq=${arr[0]-1}
        num_coordo=${arr[1]-1}
        num_project=${arr[2]-1}
        ;;
    n)
        INIT_ONLY=1
        AUTO=1
        ;;
    h)
        echo """$0
          -t: exec testfield
          -d: exec devtest
          -a: auto start (use trunk branches)
          -c: currency eur/chf
          -n: init only do not start mkdb
          -i: #instances ex: 1-2-2 for 1 hq, 2 coordos, 2 projects (default: 1-1-1)
          -f: full tree instances: HQ1C1(P1/P2) H1C2P1 H1C1
          -l: lang es/fr
          -m: mkdb branch
          -u: load acl
          -s: server branch
          -w: web branch
        """
        exit 1
    esac
done

shift $((OPTIND - 1))
REV="$1"

[ -z "$REV" ] && echo "Please specify revision: dsp-utp141 for example" && exit 1
BRANCHES="branches/$REV"

if [ "$AUTO" ]; then
    if [ ! -d LOG/ ]; then
        mkdir LOG/
    fi
    LOGFILE=LOG/$REV.log
    echo > $LOGFILE
    correct='y'
    if [ -d /home/$REV ]; then
        echo "Dir /home/$REV exists"
        exit 1
    fi
    set -o errexit
    trap end_of_script EXIT
    # Close STDOUT file descriptor
    exec 1<&-
    # Close STDERR FD
    exec 2<&-
    # Open STDOUT as $LOG_FILE file for read and write.
    exec 1<>$LOGFILE
    # Redirect STDERR to STDOUT
    exec 2>&1
elif [ -f "$BRANCHES" ]; then
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
        echo -n "Enter web branch [$BRANCH_DEFAULT_WEB]: "; read web
        [ -z "$web" ] && web=$BRANCH_DEFAULT_WEB
        echo -n "Enter env branch [$BRANCH_DEFAULT_ENV]: "; read env
        [ -z "$env" ] && env=$BRANCH_DEFAULT_ENV
    fi
    echo "Please check the branches:"
    echo "+ Unifield Server: $server"
    echo "+ Unifield Web: $web"
    echo "+ Unifield Sync Env: $env"
    echo -n "=> Is it correct? [Y] "; read correct
    [ -z "$correct" ] && correct=y
done

echo "server=\"$server\"" > $BRANCHES
echo "web=\"$web\"" >> $BRANCHES
echo "env=\"$env\"" >> $BRANCHES

IFS='_'
arrIN=($REV)
IFS='-'
arrM=($arrIN)
MAILTO=$arrM
unset IFS


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
    -e "s#@@UF_PASSWORD@@#${UF_PASSWORD}#g" \
    -e "s#@@WEB_ADMIN_PASS@@#${web_admin_pass}#g" \
    -e "s#@@WEB_LOGIN_USER@@#${web_login_user}#g" \
    -e "s#@@WEB_LOGIN_PASS@@#${web_login_pass}#g" \
    -e "s#@@NUM_HQ@@#${num_hq}#g" \
    -e "s#@@NUM_COORDO@@#${num_coordo}#g" \
    -e "s#@@NUM_PROJECT@@#${num_project}#g" \
    -e "s#@@ADDONSDIR@@#${ADDONSDIR}#g" \
    -e "s#@@MAILTO@@#${MAILTO}#g" \
    -e "s#@@MKDB_LANG@@#${MKDB_LANG}#g" \
    -e "s#@@MKDB_CURR@@#${MKDB_CURR}#g" \
    -e "s#@@COMMENT_ACL@@#${COMMENT_ACL}#g" \
    -e "s#@@FULL_TREE@@#${FULL_TREE}#g" \
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
    cp ./File/perf.wsgi /home/${USERERP}/
    chmod +x /home/${USERERP}/build_and_test.sh
    chown ${USERERP}.${USERERP} /home/${USERERP}/etc/openerp-web.cfg /home/${USERERP}/etc/openerprc /home/${USERERP}/sync_env_script/config.py /home/${USERERP}/.bash_profile /home/${USERERP}/build_and_test.sh /home/${USERERP}/runtests.sh /home/${USERERP}/perf.wsgi
    update-rc.d ${USERERP}-web defaults
    update-rc.d ${USERERP}-server defaults
    chmod +x /etc/init.d/${USERERP}-web /etc/init.d/${USERERP}-server
}

bzr_type=branch
init_user() {
    su - postgres -c -- "psql -c 'DROP ROLE IF EXISTS \"${USERERP}\";'"
    su - postgres -c -- "createuser -S -R -d ${USERERP}"
    if [ ! -d /home/${USERERP}/.bzr ]; then
        cp -a  ${template_dir}/.bzr ${template_dir}/tmp /home/${USERERP}/
    fi
    chown -R ${USERERP}.${USERERP} /home/${USERERP}/.bzr /home/${USERERP}/tmp
    su - ${USERERP} <<EOF

echo bzr ${bzr_type} "${web:=${BRANCH_DEFAULT_WEB}}" unifield-web
bzr ${bzr_type} "${web:=${BRANCH_DEFAULT_WEB}}" unifield-web
echo bzr ${bzr_type} "${server:=${BRANCH_DEFAULT_SERVER}}" unifield-server
bzr ${bzr_type} "${server:=${BRANCH_DEFAULT_SERVER}}" unifield-server
echo bzr ${bzr_type} "${env:=${BRANCH_DEFAULT_ENV}}" sync_env_script
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
Testfield PGPORT: $PGPORT
Testfield: http://${USERERP}.testfield.${rb_server_url}
URL: http://${USERERP}.${rb_server_url}
""" > /home/${USERERP}/RB_info.txt

cat /home/${USERERP}/RB_info.txt

if [[ "$TESTFIELD" ]]; then
    su - $USERERP -c "./runtests.sh test"
elif [[ "$DEVTEST" ]]; then
    su - $USERERP -c ./build_and_test.sh
elif [[ -z "$INIT_ONLY" ]]; then
    su - $USERERP -c ./sync_env_script/mkdb.py
fi
exit 0
