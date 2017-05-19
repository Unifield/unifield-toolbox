#!/usr/bin/env bash

#set -o nounset
set -o pipefail
[ -f ~/unifield-venv/bin/activate ] && . ~/unifield-venv/bin/activate

end_of_script() {
    if [[ $? -ne 0 ]]; then
        STATUS='FAILED'
    else
        STATUS=''
    fi
    send_mail $STATUS
}

send_mail() {
    if [[ -z "${MAILTO}" ]]; then
        IFS='_'
        arrIN=(`whoami`)
        IFS='-'
        arrM=($arrIN)
        MAILTO=$arrM
        unset IFS
    fi
    TMPFILE="/tmp/tetfield$$"
    cp ~/RB_info.txt $TMPFILE
    if [[ -f "${DIREXPORT}/meta" ]]; then
        cat ${DIREXPORT}/meta >> $TMPFILE
    fi
    #if [ "${VERB}" == "test" -a -d $DIREXPORT/dumps ]; then
    #    echo "Db dumps in $DIREXPORT/dumps" >> $TMPFILE
    #fi
    if [[ -n "$STY" ]]; then
        echo "screen -r -d $STY" >> $TMPFILE
    fi
    if [[ -d "${SERVERDIR}" ]]; then
        echo "==== unifield-server ====" >> $TMPFILE
        cd ${SERVERDIR}
        bzr info >> $TMPFILE
        bzr version-info >> $TMPFILE
    fi
    if [[ -d "${WEBDIR}" ]]; then
        echo "==== unifield-web ====" >> $TMPFILE
        cd ${WEBDIR}
        bzr info >> $TMPFILE
        bzr version-info >> $TMPFILE
    fi
    mail -s "Testfield `whoami` $VERB ${TEST_NAME} ${1}" $MAILTO < $TMPFILE
    rm -f $TMPFILE
}

kill_deletedb() {
    echo ${PGDATADIR}/postmaster.pid
    if [[ -f ${PGDATADIR}/postmaster.pid ]]; then
        $DBPATH/pg_ctl stop -m immediate -D $PGDATADIR 
    fi
    if [[ -d ${PGDATADIR} ]]; then
        rm -fr ${PGDATADIR}
    fi
}

kill_processes() {
    tmux kill-session -t unifield
    if [[ -f ${MYTMPDIR}/etc/web.pid ]]; then
        kill -9 `cat ${MYTMPDIR}/etc/web.pid`
    fi
    kill_deletedb
}


if [[ $# -lt 1 || ( "$1" != "benchmark" && "$1" != "test" && "$1" != "setup" && "$1" != "kill") ]];
then
    echo "Usage: "
    echo "  $0 benchmark [[name] [server_branch] [web_branch] [lettuce_param]]"
    echo "  $0 test [[name] [server_branch] [web_branch] [lettuce_param]]"
    echo "  $0 setup [[server_branch] [web_branch]]"
    echo "  $0 kill"
    exit 1
fi

source config.sh
MYTMPDIR=$SERVER_TMPDIR
PGDATADIR=$SERVER_TMPDIR/pgdata-$USER
PGRUNDIR=$SERVER_TMPDIR/pgrun-$USER

kill_processes
if [[ "$1" == "kill" ]]; then
    exit 0
fi

set -o errexit
trap end_of_script EXIT

if [[ ! -d testfield ]]; then
    git clone https://github.com/Unifield/testfield.git
    if [[ -d ~/unifield-venv ]]; then
        pip install -r testfield/requirements.txt
    fi
    #git clone https://github.com/jftempo/testfield.git
fi

/etc/init.d/${USER}-server stop
/etc/init.d/${USER}-web stop
cp config.sh testfield/
cd testfield

VERB=${1:-test}
if [[ "$VERB" == "benchmark" ]]; then
    export KEY_FETCH=$KEY_FETCH_BENCH
fi
ENVNAME=$SERVER_ENVNAME

SERVERDIR=$MYTMPDIR/unifield-server
WEBDIR=$MYTMPDIR/unifield-web

SESSION_NAME=unifield-$$


NAME=${2:-`date +%Y-%m-%d-%H%M`}

ONLY_SETUP="no"
if [[ "$VERB" == "setup" ]]; then
    ONLY_SETUP="yes"
    SERVERBRANCH=${2}
    WEBBRANCH=${3}
else
    SERVERBRANCH=${3}
    WEBBRANCH=${4}
    LETTUCE_PARAMS="${*:5}"
fi

./fetch/owncloud/fetch.sh
RUNFIRST="meta_features/A_run_first"
mkdir $RUNFIRST
TO_RUN_FIRST=(
   "supply/Cancel and Tickets"
   "supply/A_Complete_flow_from_ IR_PROJ.meta_feature"
   "supply/Tickets/US-839_Import_Order_ NOM_Prod_to ESC.meta_feature"
   "finance/HQ split entry_verify negative amounts can be split and correct dates and amounts are used.meta_feature"
   "finance/1_HQ split entry_verify negative amounts can be split and correct dates and amounts are used.meta_feature"
)

for tomove in "${TO_RUN_FIRST[@]}"; do
    if [ -d "meta_features/${tomove}" ]; then
        mv "meta_features/${tomove}"/* ${RUNFIRST}
    elif [ -f "meta_features/${tomove}" ]; then
        mv "meta_features/${tomove}" ${RUNFIRST}
    fi
done

if [ -f "meta_features/1_run/Supply/FO_SCRATCH_VAL.meta_feature" ]; then
    mv "meta_features/1_run/Supply/FO_SCRATCH_VAL.meta_feature" "meta_features/supply/"
fi

if [ -f "meta_features/IT/user_account_management/us1381-UserAccountMgmt-6.meta_feature" ]; then
	sed -i "s/TESTS_HQ1C1/HQ1C1/" meta_features/IT/user_account_management/us1381-UserAccountMgmt-6.meta_feature
fi

if [[ -n "${SERVERBRANCH}" ]]; then
    rm -fr ${SERVERDIR}
    bzr branch ${SERVERBRANCH} ${SERVERDIR}
fi

if [[ -n "${WEBBRANCH}" ]]; then
    rm -fr ${WEBDIR}
    bzr branch ${WEBBRANCH} ${WEBDIR}
fi

export PGPASSWORD=$DBPASSWORD

PARAM_UNIFIELD_SERVER="--db_user=$DBUSERNAME --db_port=$DBPORT --db_password=$DBPASSWORD --db_host=$DBADDR -c $MYTMPDIR/etc/openerprc"

FAKETIME_ARG=''
if [[ ${FORCED_DATE} ]]; then
    ORIG=`date -d ${FORCED_DATE} '+%s'`
    NOW=`date '+%s'`
    DELAY=$[ $NOW - $ORIG ]
    if [ -f /usr/local/lib/faketime/libfaketime.so.1 ]; then
        FAKETIME_ARG="FAKETIME=-${DELAY}s LD_PRELOAD=/usr/local/lib/faketime/libfaketime.so.1"
    else
        FAKETIME_ARG="FAKETIME=-${DELAY}s LD_PRELOAD=/usr/lib/faketime/libfaketime.so.1"
    fi
fi

upgrade_server()
{
    # at first we have to upgrade all the databases
    sed -i.bak "s/FOR UPDATE NOWAIT//g" $SERVERDIR/bin/addons/base/ir/ir_sequence.py
    echo "88888888888888888888888888888888
66f490e4359128c556be7ea2d152e03b 2013-04-27 16:49:56" > $SERVERDIR/bin/unifield-version.txt
    for DBNAME in $DATABASES;
    do
        REAL_NAME=$DBNAME
        if [[ "$DBPREFIX" ]]
        then
            REAL_NAME=${DBPREFIX}_${REAL_NAME}
        fi

        echo $FAKETIME_ARG python $SERVERDIR/bin/openerp-server.py $PARAM_UNIFIELD_SERVER -u base --stop-after-init -d $REAL_NAME
        eval $FAKETIME_ARG python $SERVERDIR/bin/openerp-server.py $PARAM_UNIFIELD_SERVER -u base --stop-after-init -d $REAL_NAME
    done
}


run_unifield()
{
    # we print the commands to launch the components in a separate window in order to debug.
    #  We'll launch them later in a tmux
    echo "Run the web server:" $FAKETIME_ARG python $WEBDIR/openerp-web.py -c $MYTMPDIR/etc/openerp-web.cfg
    echo "Run the server:" $FAKETIME_ARG python $SERVERDIR/bin/openerp-server.py $PARAM_UNIFIELD_SERVER

    tmux new -d -s $SESSION_NAME -n server "
        $FAKETIME_ARG python $SERVERDIR/bin/openerp-server.py $PARAM_UNIFIELD_SERVER
        "
    tmux new-window -t $SESSION_NAME -n web "
        $FAKETIME_ARG python $WEBDIR/openerp-web.py -c $MYTMPDIR/etc/openerp-web.cfg
        "
    sleep 20
}

run_lettuce()
{
    case $VERB in

    test)
        export TIME_BEFORE_FAILURE=${TIME_BEFORE_FAILURE:-70}
        export COUNT=6;

        export TEST_DESCRIPTION=${TEST_DESCRIPTION:-$NAME}
        export TEST_NAME=${TEST_NAME:-$NAME}
        export TEST_DATE=`date +%Y/%m/%d`

        rm -fr output/* || true

        ./runtests_local.sh $LETTUCE_PARAMS || true

        WEBVERSION=`bzr revno --tree $WEBDIR`
        SERVERVERSION=`bzr revno --tree $SERVERDIR`
        DBVERSION=`find instances/$ENVNAME -name '*.dump' -exec md5sum {} \; | md5sum`
        METAVERSION=`find features/ -name '*.feature' -exec md5sum {} \; | md5sum`
        TESTVERSION=`git rev-parse HEAD`
        echo "S${SERVERVERSION} W${WEBVERSION} D${DBVERSION:0:10} M${METAVERSION:0:10} T${TESTVERSION:0:10}" > output/version

        DIREXPORT=website/tests/$NAME
        if [[ -e "$DIREXPORT" ]]
        then
            rm -rf "$DIREXPORT" || true
        fi
        mkdir -p "$DIREXPORT"

        mkdir output/dumps
        #for DBNAME in $DATABASES; do
        #        pg_dump -h $DBADDR -p $DBPORT -Fc $DBNAME > output/dumps/$DBNAME.dump
        #done


        cp -R output/* $DIREXPORT/ || true

        ;;

    benchmark)
        rm -rf results/* 2> /dev/null || true
        export TIME_BEFORE_FAILURE=

        for count in 5 15 25 35 45
        do
            export COUNT=$count

            # run the benchmark
            for nb in `seq 1 3`;
            do
                ./runtests_local.sh -t testperf $LETTUCE_PARAMS || true
            done
        done

        DIREXPORT="website/performances/$NAME"
        if [[ -e "$DIREXPORT" ]]
        then
            rm -rf "$DIREXPORT" || true
        fi
        mkdir -p "$DIREXPORT"

        cp -R results/* "$DIREXPORT/"

        ;;

    esac
}


launch_database()
{
    # we have to setup a database if required
    LAUNCH_DB=
    if [[ ${DBPATH} && ${FORCED_DATE} ]];
    then
        DBADDR=localhost
        kill_deletedb
        mkdir -p $PGDATADIR $PGRUNDIR

        $DBPATH/initdb --username=$USER --encoding=UTF8 $PGDATADIR

        echo "port = $DBPORT" >> $PGDATADIR/postgresql.conf
        echo "unix_socket_directory = '$PGRUNDIR'" >> $PGDATADIR/postgresql.conf
        #echo "shared_buffers = 1GB" >> $PGDATADIR/postgresql.conf
        echo 'checkpoint_segments = 10' >> $PGDATADIR/postgresql.conf
        echo 'checkpoint_completion_target = 0.9' >> $PGDATADIR/postgresql.conf
        #echo 'work_mem = 50MB' >> $PGDATADIR/postgresql.conf
        #echo 'maintenance_work_mem = 512MB' >> $PGDATADIR/postgresql.conf
        echo 'random_page_cost = 2.0' >> $PGDATADIR/postgresql.conf
        #LAUNCH_DB="$FAKETIME_ARG $DBPATH/postgres -D $PGDATADIR"
        #tmux new -d -s PostgreSQL_$$ "$LAUNCH_DB; read"
        export PGPORT=$DBPORT
        export PGHOST=127.0.0.1
        eval $FAKETIME_ARG $DBPATH/pg_ctl -w start -D $PGDATADIR -l $PGRUNDIR/postgresql.log
        psql -h $DBADDR -p $DBPORT postgres -c "CREATE USER $DBUSERNAME WITH CREATEDB PASSWORD '$DBPASSWORD'" || echo $?

    else
        FORCED_DATE=
    fi
}

DATABASES=
for FILENAME in `find instances/$ENVNAME -name *.dump | sort`;
do
    F_WITHOUT_EXTENSION=${FILENAME%.dump}
    DBNAME=${F_WITHOUT_EXTENSION##*/}

    DATABASES="$DATABASES $DBNAME"
done
FIRST_DATABASE=`echo $DATABASES | cut -d " " -f1`

export DATABASES=$DATABASES

./generate_credentials.sh $FIRST_DATABASE $DBPREFIX
launch_database

python restore.py --reset-sync --reset-versions $ENVNAME

if [[ "$RELOAD_BASE_MODULE" != 'no' ]]
then
    upgrade_server
fi

run_unifield

if [[ $ONLY_SETUP == "yes" ]]
then
    echo "Setup done!"
    exit 0
fi

run_lettuce
#kill_processes
