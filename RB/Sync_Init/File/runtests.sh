#!/usr/bin/env bash

#set -o nounset
set -o pipefail

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
    if [ "${VERB}" == "test" -a -d $DIREXPORT/dumps ]; then
        echo "Db dumps in $DIREXPORT/dumps" >> $TMPFILE
    fi
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

kill_processes() {
    tmux kill-session -t unifield
    if [[ -f ${MYTMPDIR}/etc/web.pid ]]; then
        kill -9 `cat ${MYTMPDIR}/etc/web.pid`
    fi
    tmux kill-session -t PostgreSQL
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

if [[ "$1" == "kill" ]]; then
    kill_processes
    exit 0
fi

set -o errexit
trap end_of_script EXIT

if [[ ! -d testfield ]]; then
    git clone https://github.com/hectord/testfield.git
    cp -f ~/perf.wsgi testfield/website
fi

/etc/init.d/${USER}-server stop
/etc/init.d/${USER}-web stop
cp config.sh testfield/
cd testfield

VERB=${1:-test}
if [[ "$VERB" == "benchmark" ]]; then
    export KEY_FETCH=$KEY_FETCH_BENCH
fi
./fetch/owncloud/fetch.sh
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


upgrade_server()
{
    # at first we have to upgrade all the databases
    BEFORE_COMMAND=
    if [[ ${FORCED_DATE} ]]
    then
        BEFORE_COMMAND="faketime \"${FORCED_DATE} `date +%H:%M:%S`\""
    fi
    sed -i.bak "s/FOR UPDATE NOWAIT//g" $SERVERDIR/bin/addons/base/ir/ir_sequence.py
    for DBNAME in $DATABASES;
    do
        REAL_NAME=$DBNAME

        if [[ "$DBPREFIX" ]]
        then
            REAL_NAME=${DBPREFIX}_${REAL_NAME}
        fi

        echo $BEFORE_COMMAND python $SERVERDIR/bin/openerp-server.py $PARAM_UNIFIELD_SERVER -u base --stop-after-init -d $REAL_NAME
        eval $BEFORE_COMMAND python $SERVERDIR/bin/openerp-server.py $PARAM_UNIFIELD_SERVER -u base --stop-after-init -d $REAL_NAME
    done
}


run_unifield()
{
    BEFORE_COMMAND=
    if [[ ${FORCED_DATE} ]]
    then
        BEFORE_COMMAND="faketime \"${FORCED_DATE} `date +%H:%M:%S`\""
    fi

    # we print the commands to launch the components in a separate window in order to debug.
    #  We'll launch them later in a tmux
    echo "Run the web server:" $BEFORE_COMMAND python $WEBDIR/openerp-web.py -c $MYTMPDIR/etc/openerp-web.cfg
    echo "Run the server:" $BEFORE_COMMAND python $SERVERDIR/bin/openerp-server.py $PARAM_UNIFIELD_SERVER

    tmux new -d -s $SESSION_NAME -n server "
        $BEFORE_COMMAND python $SERVERDIR/bin/openerp-server.py $PARAM_UNIFIELD_SERVER
        "
    tmux new-window -t $SESSION_NAME -n web "
        $BEFORE_COMMAND python $WEBDIR/openerp-web.py -c $MYTMPDIR/etc/openerp-web.cfg
        "
    sleep 20
}

run_lettuce()
{
    case $VERB in

    test)
        export TIME_BEFORE_FAILURE=${TIME_BEFORE_FAILURE:-40}
        export COUNT=2;

        export TEST_DESCRIPTION=${TEST_DESCRIPTION:-$NAME}
        export TEST_NAME=${TEST_NAME:-$NAME}
        export TEST_DATE=`date +%Y/%m/%d`

        rm -fr output/* || true

        ./runtests_local.sh $LETTUCE_PARAMS || true

        DIREXPORT=website/tests/$NAME
        if [[ -e "$DIREXPORT" ]]
        then
            rm -rf "$DIREXPORT" || true
        fi
        mkdir "$DIREXPORT"

        mkdir output/dumps
            for DBNAME in $DATABASES; do
                pg_dump -h $DBADDR -p $DBPORT -Fc $DBNAME > output/dumps/$DBNAME.dump
        done

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
        mkdir "$DIREXPORT"

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
        DATADIR=$SERVER_TMPDIR/data-$$
        RUNDIR=$SERVER_TMPDIR/run-$$
        DBADDR=localhost

        mkdir $DATADIR $RUNDIR

        $DBPATH/initdb --username=$USER --encoding=UTF8 $DATADIR

        echo "port = $DBPORT" >> $DATADIR/postgresql.conf
        echo "unix_socket_directory = '$RUNDIR'" >> $DATADIR/postgresql.conf
        #echo "shared_buffers = 1GB" >> $DATADIR/postgresql.conf
        echo 'checkpoint_segments = 10' >> $DATADIR/postgresql.conf
        echo 'checkpoint_completion_target = 0.9' >> $DATADIR/postgresql.conf
        #echo 'work_mem = 50MB' >> $DATADIR/postgresql.conf
        #echo 'maintenance_work_mem = 512MB' >> $DATADIR/postgresql.conf
        echo 'random_page_cost = 2.0' >> $DATADIR/postgresql.conf

        LAUNCH_DB="faketime \"${FORCED_DATE} `date +%H:%M:%S`\" $DBPATH/postgres -D $DATADIR"
        tmux new -d -s PostgreSQL_$$ "$LAUNCH_DB; read"
        #TODO: Fix that... we should wait until psql can connect
        sleep 2
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
launch_database;

python restore.py --reset-versions $ENVNAME

if [[ "$RELOAD_BASE_MODULE" != 'no' ]]
then
    upgrade_server;
fi

run_unifield;

if [[ $ONLY_SETUP == "yes" ]]
then
    echo "Setup done!"
    exit 0
fi

DISPLAY_BEFORE=$DISPLAY

if [[ -z "$DISPLAY" ]];
then
    tmux new -d -s X_$$ "Xvfb :$$"
    export DISPLAY=:$$
fi

run_lettuce;
if [[ -z "$DISPLAY_BEFORE" ]];
then
    tmux kill-session -t X_$$
    pkill -f "Xvfb :$$"
fi

kill_processes

if [[ ${DATADIR} ]];
then
    rm -rf ${DATADIR}
fi

if [[ ${RUNDIR} ]];
then
    rm -rf ${RUNDIR}
fi
