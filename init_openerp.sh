#! /bin/bash

REV="sprint5-rc1sync2"

NETRPCPORT="50168"
WEBPORT="50169"
XMLRPCPORT="50170"

USERERP="openerp-${REV}"
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
    create_file ./File/openerp-server-sprint1  /etc/init.d/openerp-server-${REV}
    create_file ./File/openerp-web-sprint1 /etc/init.d/openerp-web-${REV}
    create_file ./File/openerprc /home/${USERERP}/etc/openerprc
    create_file ./File/openerp-web.cfg /home/${USERERP}/etc/openerp-web.cfg
    create_file ./File/apache.conf /etc/apache2/sites-available/${USERERP}

    chown ${USERERP}.${USERERP} /home/${USERERP}/etc/openerp-web.cfg /home/${USERERP}/etc/openerprc
    update-rc.d openerp-web-${REV} defaults
    update-rc.d openerp-server-${REV} defaults
    chmod +x /etc/init.d/openerp-web-${REV} /etc/init.d/openerp-server-${REV}
    echo "Apache: conf and reload"
}

init_user() {
    if [ -d /home/${USERERP} ]; then
         echo "User ${USERERP} exists !"
         exit 1
    fi
    useradd -s /bin/bash -d /home/${USERERP} -m ${USERERP}
    su - postgres -c -- "createuser -S -R -d ${USERERP}"
    cp -a ~dvo/.ssh/ ~dvo/.bazaar/ ~dvo/tmp/ /home/${USERERP}/
    chown -R ${USERERP}.${USERERP} /home/${USERERP}/.ssh /home/${USERERP}/.bazaar ~dvo/tmp/
    su - ${USERERP} <<EOF
bzr checkout --lightweight lp:unifield-wm/${BZBRANCH} unifield-wm
bzr checkout --lightweight lp:unifield-addons/${BZBRANCH} unifield-addons
bzr checkout --lightweight lp:unifield-web/${BZBRANCH} unifield-web
bzr checkout --lightweight lp:unifield-server/${BZBRANCH} unifield-server
bzr checkout --lightweight lp:unifield-toolbox 
bzr checkout --lightweight lp:~unifield-team/unifield-wm/unifield-data
bzr checkout --lightweight lp:~unifield-team/unifield-wm/sync_module_prod
mkdir etc log
createdb ${DBNAME}
#cd /home/${USERERP}/unifield-server/bin/
echo unifield-server/bin/openerp-server.py -c ../../etc/openerprc -d ${DBNAME} --without-demo=all -i msf_profile
echo Configure http://${REV}.dsp.uf3.unifield.org/
echo python blk_import.py -d ${DBNAME} -p ${XMLRPCPORT} /home/${USERERP}/unifield-data/
EOF
}

init_user
config_file
