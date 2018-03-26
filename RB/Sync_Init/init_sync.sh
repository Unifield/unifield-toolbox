#!/bin/bash

[ -f /opt/unifield-venv/bin/activate ] && . /opt/unifield-venv/bin/activate

end_of_script() {
    if [[ $? -ne 0 ]]; then
        STATUS='FAILED'
    else
        STATUS='OK'
    fi
    if [[ -n "$TAILPID" ]]; then
        sleep 2
        kill $TAILPID
    fi
    if [[ "${STATUS}" != 'OK' || "${INIT_TYPE}" != 'devtests' ]]; then
        send_mail $STATUS
    fi
}
send_mail() {
    TMPFILE=/tmp/mkdb$$
    cat /home/$USERERP/RB_info.txt > $TMPFILE
    echo >> $TMPFILE
    echo >> $TMPFILE
    echo "---------------" >> $TMPFILE
    cat $LOGFILE >> $TMPFILE
    mail -a 'Content-Type: text/plain' -s "RB ${REV} ${1}" $MAILTO < $TMPFILE
    rm -f $TMPFILE
}
WITH_SSL="Yes"
BRANCH_DEFAULT_SERVER="lp:unifield-server"
BRANCH_DEFAULT_WEB="lp:unifield-web"
BRANCH_DEFAULT_ENV="lp:~unifield-team/unifield-wm/sync-env"
CERTBOT_SCRIPT="~/certbot/certbot-auto"
POSTGRES_CER=""
POSTGRES_KEY=""
if [[ -f ~/RBconfig ]]; then
    source ~/RBconfig
fi
PROTO='http'
cd `dirname $0`
TAILPID=
AUTO=
MKDB_LANG="'fr_MF'"
MKDB_CURR='eur'
num_hq=1
num_coordo=1
INIT_TYPE="mkdb"
COMMENT_ACL=
FULL_TREE='"""'
INTERMISSION_TREE='"""'
INTERSECTION_TREE='"""'
JIRA=
SET_RB=
RB_PREFIX=
BUILD_PYTHON_ENV=
while getopts t:i:s:w:m:l:c:p:auULfhjrev opt; do
case $opt in
    t)
         if [[ "$OPTARG" != "mkdb" && "$OPTARG" != "testfield" && "$OPTARG" != "devtests" && "$OPTARG" != "testfield_partial" && "$OPTARG" != "none" ]]; then
             echo "-t option should be mkdb|testfield|testfield_partial|devtests|none"
             exit 1
        fi
        INIT_TYPE=$OPTARG
        if [[ "$INIT_TYPE" == "devtests" ]]; then
            num_project=2
        fi
        AUTO=1
        ;;
    r)
        SET_RB=1
        ;;
    e)
        WITH_SSL="Yes"
        ;;
    p)
        RB_PREFIX=$OPTARG
        ;;
    j)
        JIRA=1
        ;;
    i)
        AUTO=1
        if [[ "$OPTARG" == "s" ]]; then
            INTERSECTION_TREE=""
        elif [[ "$OPTARG" == "m" ]]; then
            INTERMISSION_TREE=""
        else
            IFS="-"
            arr=($OPTARG)
            unset IFS
            num_hq=${arr[0]-1}
            num_coordo=${arr[1]-1}
            num_project=${arr[2]-1}
        fi
        ;;
    v)
        BUILD_PYTHON_ENV=1
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
    L)
        MKDB_LANG="False"
        #AUTO=1
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
    u)
        ;;
    U)
        AUTO=1
        COMMENT_ACL='"""'
        ;;
    f)
        AUTO=1
        FULL_TREE=
        ;;
    h)
        echo """$0
          -t [mkdb|testfield|testfield_partial|devtests|none]: command to start (default: mkdb)
          -a: start mkdb with trunk branches
          -e: encrypt (use ssl proxy)
          -v: build a new virtual env

          # MKDB options
          -c: currency eur/chf
          -i: #instances ex: 1-2-2 for 1 hq, 2 coordos, 2 projects (default: 1-1-1) / s for HQ1C1{1,2}P1 + HQ1C1 / m for HQ1C{1,2}P1
          -f: full tree instances: HQ1C1(P1/P2) H1C2P1 H1C1
          -L: do not load fr lang
          -m: mkdb branch
          -U: dot not load acl

          -j: get launchpad branches from Jira ticket
          -r: set RB field in Jira (if -j is used)
          -p: change RB prefix name
          -s: server branch
          -w: web branch
        """
        exit 1
    esac
done

if [[ "$WITH_SSL" == "Yes" ]]; then
    PROTO='https'
fi

shift $((OPTIND - 1))
REV="$1"

[ -z "$REV" ] && echo "Please specify revision: dsp-utp141 for example" && exit 1
BRANCHES="branches/$REV"

if [ "$JIRA" ]; then
    jira=($(python Jira/get_branch.py $REV))
    if [[ $? -ne 0 ]]; then
        echo "Jira Error"
        exit 1
    fi
    if [[ -z "$server" ]]; then
        server=${jira[0]}
    fi
    if [[ -z "$web" ]]; then
        web=${jira[1]}
    fi
    if [[ -z "$RB_PREFIX" ]]; then
        RB_PREFIX=${jira[2]}
    fi
    AUTO=1
fi

if [[ -n "$RB_PREFIX" ]]; then
        REV="${RB_PREFIX}-${REV}"
fi

# lower RB name
REV=${REV,,}

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
    echo "Running ..."
    tail -f $LOGFILE &
    TAILPID=$!
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
    INIT_TYPE=
else
    correct=no
    INIT_TYPE=
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
XMLRPCSPORT=${userid}5

ADDONS=""
ADDONSDIR="'unifield-server', 'unifield-web'"
UNIFIELDTEST="/home/${USERERP}/unifield-server/bin/addons/unifield_tests/"

SYNC_USER_LOGIN=""
SYNC_USER_PASSWORD=""

create_file() {
sed -e "s#@@USERERP@@#${USERERP}#g" \
    -e "s#@@DBNAME@@#${DBNAME}#g" \
    -e "s#@@XMLRPCPORT@@#${XMLRPCPORT}#g" \
    -e "s#@@XMLRPCSPORT@@#${XMLRPCSPORT}#g" \
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
    -e "s#@@APACHE_PROD_USER@@#${APACHE_PROD_USER}#g" \
    -e "s#@@APACHE_PROD_PASSWORD@@#${APACHE_PROD_PASSWORD}#g" \
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
    -e "s#@@SYNC_USER_LOGIN@@#${SYNC_USER_LOGIN}#g" \
    -e "s#@@SYNC_USER_PASSWORD@@#${SYNC_USER_PASSWORD}#g" \
    -e "s#@@PROTO@@#${PROTO}#g" \
    -e "s#@@PG_PATH@@#${PG_PATH:=}#g" \
    -e "s#@@DBPATH@@#${PG_PATH:=/usr/lib/postgresql/8.4/bin/}#g" \
    -e "s#@@INTERMISSION_TREE@@#${INTERMISSION_TREE}#g" \
    -e "s#@@INTERSECTION_TREE@@#${INTERSECTION_TREE}#g" \
    -e "s#@@POSTGRES_CER@@#${POSTGRES_CER}#g" \
    -e "s#@@POSTGRES_KEY@@#${POSTGRES_KEY}#g" \
    -e "s#@@WEBPORT@@#${WEBPORT}#g" $1  > $2
}


config_file() {
    if [[ "$POSTGRES_CER" ]]; then
        DEST="/home/${USERERP}/.uf6_psql_cer"
        cp $POSTGRES_CER $DEST
        chown ${USERERP} $DEST
        chmod 600 $DEST
        POSTGRES_CER=$DEST
    fi

    if [[ "$POSTGRES_KEY" ]]; then
        DEST="/home/${USERERP}/.uf6_psql_key"
        cp $POSTGRES_KEY $DEST
        chown ${USERERP} $DEST
        chmod 600 $DEST
        POSTGRES_KEY=$DEST

    fi
    create_file ./File/openerp-server-sprint1  /etc/init.d/${USERERP}-server
    create_file ./File/openerp-web-sprint1 /etc/init.d/${USERERP}-web
    create_file ./File/openerpallrc /home/${USERERP}/etc/openerprc
    create_file ./File/sync-envall.py /home/${USERERP}/sync_env_script/config.py
    create_file ./File/unifield.config /home/${USERERP}/unifield.config
    create_file ./File/bash_profile2 /home/${USERERP}/.bash_profile
    create_file ./File/restore_dumprc /home/${USERERP}/.restore_dumprc
    create_file ./File/config.sh /home/${USERERP}/config.sh
    create_file ./File/build_and_test_all /home/${USERERP}/build_and_test.sh
    create_file ./File/runtests.sh /home/${USERERP}/runtests.sh

if [[ "$WITH_SSL" == "Yes" ]]; then
    create_file ./File/apache-1ssl.conf /etc/apache2/sites-available/${USERERP}.conf
    a2ensite ${USERERP}.conf
    create_file ./File/openerp-web-ssl.cfg /home/${USERERP}/etc/openerp-web.cfg
else
    create_file ./File/apache.conf /etc/apache2/sites-available/${USERERP}.conf
    a2ensite ${USERERP}.conf
    create_file ./File/openerp-web.cfg /home/${USERERP}/etc/openerp-web.cfg

fi
    cp ./File/runtests_partial.sh /home/${USERERP}/
    chmod +x /home/${USERERP}/runtests.sh /home/${USERERP}/build_and_test.sh
    chown ${USERERP}.${USERERP} /home/${USERERP}/etc/openerp-web.cfg /home/${USERERP}/etc/openerprc /home/${USERERP}/sync_env_script/config.py /home/${USERERP}/.bash_profile /home/${USERERP}/build_and_test.sh /home/${USERERP}/runtests.sh /home/${USERERP}/runtests_partial.sh
    chmod +x /etc/init.d/${USERERP}-web /etc/init.d/${USERERP}-server
    update-rc.d ${USERERP}-web defaults
    update-rc.d ${USERERP}-server defaults
}

bzr_type=branch
init_user() {
    su - ${PG_USER} -c -- "${PG_PATH}psql -c 'DROP ROLE IF EXISTS \"${USERERP}\";'"
    su - ${PG_USER} -c -- "${PG_PATH}createuser -S -R -d ${USERERP}"
    if [ ! -d /home/${USERERP}/.bzr ]; then
        cp -a  ${template_dir}/.bzr ${template_dir}/tmp /home/${USERERP}/
    fi

    chown -R ${USERERP}.${USERERP} /home/${USERERP}/.bzr /home/${USERERP}/tmp
    su - ${USERERP} <<EOF

echo bzr ${bzr_type} ${web:=${BRANCH_DEFAULT_WEB}} unifield-web
bzr ${bzr_type} ${web:=${BRANCH_DEFAULT_WEB}} unifield-web
echo bzr ${bzr_type} ${server:=${BRANCH_DEFAULT_SERVER}} unifield-server
bzr ${bzr_type} ${server:=${BRANCH_DEFAULT_SERVER}} unifield-server
echo bzr ${bzr_type} ${env:=${BRANCH_DEFAULT_ENV}} sync_env_script
bzr ${bzr_type} ${env:=${BRANCH_DEFAULT_ENV}} sync_env_script

mkdir etc log exports
EOF

    if [[ -f "/home/${USERERP}/unifield-server/tools/.ok_admin_sync" ]]; then
		SYNC_USER_LOGIN="admin"
		SYNC_USER_PASSWORD=$(echo -n $web_admin_pass | base64)
	fi

    if [[ -n "${BUILD_PYTHON_ENV}" ]]; then
	su - ${USERERP} <<EOF
virtualenv -p ${PYTHON_EXE} /home/${USERERP}/unifield-venv
. /home/${USERERP}/unifield-venv/bin/activate
cd unifield-server
python setup.py develop
pip install -U setuptools
pip install bzr
pip install bzrtools
pip install easywebdav
pip install jira
pip install httplib2
cd ../unifield-web
python setup.py develop
EOF
    fi
    if [[ -f /opt/unifield-venv/bin/activate &&  ! -d /home/${USERERP}/unifield-venv ]]; then
	 ln -s /opt/unifield-venv /home/${USERERP}/unifield-venv
    fi
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

if [[ "$WITH_SSL" == "Yes" ]]; then
    ${CERTBOT_SCRIPT} certonly -n --webroot -w /var/www -d ${USERERP}.${rb_server_url}
    create_file ./File/apache-ssl.conf /etc/apache2/sites-available/${USERERP}.conf
    /etc/init.d/apache2 reload
fi

echo """Net-RPC port: $NETRPCPORT
XML-RPC port: $XMLRPCPORT
XML-RPCS port: $XMLRPCSPORT
HTML port: $WEBPORT
Testfield PGPORT: $PGPORT
Testfield: http://${USERERP}.testfield.${rb_server_url}
URL: ${PROTO}://${USERERP}.${rb_server_url}
""" > /home/${USERERP}/RB_info.txt

cat /home/${USERERP}/RB_info.txt

case $INIT_TYPE in
  testfield)
    su - $USERERP -c "./runtests.sh test"
    ;;
  testfield_partial)
    PY_PATH=""
    if [[ -f /home/$USERERP/unifield-venv/bin/python ]]; then
        PY_PATH="/home/$USERERP/unifield-venv/bin/"
    fi
    su - $USERERP -c "${PY_PATH}python ./sync_env_script/mkdb.py"
    su - $USERERP -c "./runtests_partial.sh test"
    ;;
  devtests)
    su - $USERERP -c ./build_and_test.sh
    ;;
  mkdb)
    PY_PATH=""
    if [[ -f /home/$USERERP/unifield-venv/bin/python ]]; then
        PY_PATH="/home/$USERERP/unifield-venv/bin/"
    fi
    su - $USERERP -c "${PY_PATH}python ./sync_env_script/mkdb.py"
    echo "su - $USERERP"
    echo "${PROTO}://${USERERP}.${rb_server_url}"
    ;;
  *)
    echo "Please run ./mkdb.py as user $USERERP to finish:"
    echo "su - $USERERP"
    echo "cd ~/sync_env_script; python mkdb.py"
    ;;
esac

if [[ "$JIRA" && "$SET_RB" ]]; then
    python Jira/set_rb.py $1 ${PROTO}://${USERERP}.${rb_server_url}
fi

# add some alias to make easier the RB managment:
echo "alias webrestart='/etc/init.d/$USERERP-web restart'
alias serverrestart='/etc/init.d/$USERERP-server restart'
alias webstart='/etc/init.d/$USERERP-web start'
alias webstop='/etc/init.d/$USERERP-web stop'
alias serverstart='/etc/init.d/$USERERP-server start'
alias serverstop='/etc/init.d/$USERERP-server stop'
alias servertail='tail -f -n 100 ~/log/openerp-server.log'
function update_all_dbs() {
   for x in \`psql -td template1 -c \"SELECT datname FROM pg_database WHERE pg_get_userbyid(datdba) = current_user;\"\`; do
       /home/$USERERP/unifield-server/bin/openerp-server.py -c /home/$USERERP/etc/openerprc -d \$x -u base --stop-after-init
   done
}
XMLRPCPORT=$XMLRPCPORT
TFPGPORT=$PGPORT
NETRPCPORT=$NETRPCPORT
HTMLPORT=$WEBPORT
" >> /home/${USERERP}/.bashrc


exit 0
