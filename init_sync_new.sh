#! /bin/bash

BRANCH_DEFAULT_SERVER="lp:unifield-server"
BRANCH_DEFAULT_ADDONS="lp:unifield-addons"
BRANCH_DEFAULT_WEB="lp:unifield-web"
BRANCH_DEFAULT_WM="lp:~unifield-team/unifield-wm/sprint5"
BRANCH_DEFAULT_SYNC="lp:~unifield-team/unifield-wm/sync_module_prod"
BRANCH_DEFAULT_ENV="lp:~unifield-team/unifield-wm/sync_env_script"

REV="$1"
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

read NETRPCPORT WEBPORT XMLRPCPORT <<<`netstat -anltp 2> /dev/null | perl -e '%port = ();
($min, $max) = (50200, 50999);
while(<>) {
    $port{$&} = 1 if m/:\K\d+\b/ and $& >= $min and $& <= $max;
}
for my $i ($min..$max) {
    if( not exists $port{$i} and
        not exists $port{$i+1} and
        not exists $port{$i+2}) {
            print join(" ", $i, $i+1, $i+2);
            last;
    }
}'`
URL="http://$REV.dsp.uf3.unifield.org:$WEBPORT"

USERERP=${REV}
APACHEPORT="80"
APACHEHOST=${REV}
DBNAME="${REV}"
BZBRANCH=""
ADMINDBPASS="4unifield"

create_file() {
sed -e "s#@@USERERP@@#${USERERP}#g" \
    -e "s#@@DBNAME@@#${DBNAME}#g" \
    -e "s#@@XMLRPCPORT@@#${XMLRPCPORT}#g" \
    -e "s#@@NETRPCPORT@@#${NETRPCPORT}#g" \
    -e "s#@@ADMINDBPASS@@#${ADMINDBPASS}#g" \
    -e "s#@@APACHEPORT@@#${APACHEPORT}#g" \
    -e "s#@@APACHEHOST@@#${APACHEHOST}#g" \
    -e "s#@@WEBPORT@@#${WEBPORT}#g" $1  > $2
}


config_file() {
    create_file ./File/openerp-server-sprint1  /etc/init.d/${USERERP}-server
    create_file ./File/openerp-web-sprint1 /etc/init.d/${USERERP}-web
    create_file ./File/openerprc /home/${USERERP}/etc/openerprc
    create_file ./File/openerp-web.cfg /home/${USERERP}/etc/openerp-web.cfg
    create_file ./File/apache.conf /etc/apache2/sites-available/${USERERP}
    create_file ./File/sync-env.py /home/${USERERP}/sync_env_script/config.py

    prefix=`perl -e 'opendir DIR,"/etc/apache2/sites-enabled" or die $!;%sites = map {substr($_,0,3), 1} grep {/^\d\d\d/} readdir(DIR); for(1..900){$prefix=sprintf("%03d", $_);if(not exists $sites{$prefix}){print "$prefix\n";last}}'`
    [ -z "$prefix" ] && echo "Cannot determine prefix in /etc/apache2/sites-enabled!" && exit 1
    ln -sv "../sites-available/${USERERP}" "/etc/apache2/sites-enabled/${prefix}-${USERERP}"
    chown ${USERERP}.${USERERP} /home/${USERERP}/etc/openerp-web.cfg /home/${USERERP}/etc/openerprc /home/${USERERP}/sync_env_script/config.py
    update-rc.d ${USERERP}-web defaults
    update-rc.d ${USERERP}-server defaults
    chmod +x /etc/init.d/${USERERP}-web /etc/init.d/${USERERP}-server
}

init_user() {
    useradd -s /bin/bash -d /home/${USERERP} -m ${USERERP}
    su - postgres -c -- "createuser -S -R -d ${USERERP}"
    cp -a ~dvo/.ssh/ ~dvo/.bazaar/ /home/${USERERP}/
    chown -R ${USERERP}.${USERERP} /home/${USERERP}/.ssh /home/${USERERP}/.bazaar
    su - ${USERERP} <<EOF

bzr checkout --lightweight "$wm" unifield-wm
bzr checkout --lightweight "$addons" unifield-addons
bzr checkout --lightweight "$web" unifield-web
bzr checkout --lightweight "$server" unifield-server
bzr checkout --lightweight "$sync" sync_module_prod
bzr checkout --lightweight "$env" sync_env_script

mkdir etc log
#createdb ${DBNAME}

#cd /home/${USERERP}/unifield-server/bin/
#echo unifield-server/bin/openerp-server.py -c ../../etc/openerprc -d ${DBNAME} --without-demo=all
echo Configure http://${REV}.dsp.uf3.unifield.org/
EOF
}

restart_servers() {
    echo "Apache: conf and reload"
    apache2ctl -t && /etc/init.d/apache2 restart || exit 2
    /etc/init.d/${USERERP}-server start
    /etc/init.d/${USERERP}-web start
}

init_user
config_file
restart_servers

echo "Net-RPC port: $NETRPCPORT"
echo "XML-RPC port: $XMLRPCPORT"
echo "HTML port: $WEBPORT"
echo "URL: $URL"
echo
echo "Please run ./mkdb.py as user $USERERP to finish:"
echo "su $USERERP"
echo "cd ~/sync_env_script"
echo "./mkdb.py"
