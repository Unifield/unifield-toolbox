#! /bin/bash

REV="dsp5-sp97"

NETRPCPORT="50273"
WEBPORT="50272"
XMLRPCPORT="50274"

USERERP=${REV}
APACHEPORT="80"
APACHEHOST=${REV}
DBNAME="${REV}"
BZBRANCH=""
ADMINDBPASS="4unifield"

create_file() {
sed -e "s#@@USERERP@@#${USERERP}#g" \
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

    chown ${USERERP}.${USERERP} /home/${USERERP}/etc/openerp-web.cfg /home/${USERERP}/etc/openerprc
    update-rc.d ${USERERP}-web defaults
    update-rc.d ${USERERP}-server defaults
    chmod +x /etc/init.d/${USERERP}-web /etc/init.d/${USERERP}-server
    echo "Apache: conf and reload"
}

init_user() {
    useradd -s /bin/bash -d /home/${USERERP} -m ${USERERP}
    su - postgres -c -- "createuser -S -R -d ${USERERP}"
    cp -a ~dvo/.ssh/ ~dvo/.bazaar/ /home/${USERERP}/
    chown -R ${USERERP}.${USERERP} /home/${USERERP}/.ssh /home/${USERERP}/.bazaar
    su - ${USERERP} <<EOF

bzr checkout --lightweight lp:~unifield-team/unifield-wm/sprint5 unifield-wm
bzr checkout --lightweight lp:unifield-addons unifield-addons
bzr checkout --lightweight lp:unifield-web unifield-web
bzr checkout --lightweight lp:unifield-server unifield-server
bzr checkout --lightweight lp:~unifield-team/unifield-wm/sync_sp97 sync_module_prod
bzr checkout --lightweight lp:~unifield-team/unifield-wm/sync_env_script sync_env_script

mkdir etc log
#createdb ${DBNAME}

#cd /home/${USERERP}/unifield-server/bin/
#echo unifield-server/bin/openerp-server.py -c ../../etc/openerprc -d ${DBNAME} --without-demo=all
echo Configure http://${REV}.dsp.uf3.unifield.org/
EOF
}

init_user
config_file
