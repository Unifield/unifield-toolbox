#! /bin/bash

[ -f ~/unifield-venv/bin/activate ] && . ~/unifield-venv/bin/activate


if [[ ! -d testfield ]]; then
    git clone https://github.com/jftempo/testfield.git
fi

. config.sh
echo """SRV_ADDRESS = '127.0.0.1'

DB_PREFIX = '$USER'
# Configuration variables 
XMLRPC_PORT = $XMLRPC_PORT
NETRPC_PORT = $NETRPC_PORT
HTTP_PORT = $WEB_PORT
HTTP_URL_SERVER = 'http://%s:%d' % (SRV_ADDRESS, HTTP_PORT)

# Configuration variable to generate input files / Restore dumps
DB_ADDRESS = '127.0.0.1'
DB_PORT = 12114
DB_USERNAME = 'toto'
DB_PASSWORD = 'toto'

UNIFIELD_ADMIN = 'admin'
UNIFIELD_PASSWORD = 'admin'

SERVER_HWID = ''
USING_DOCKER = False
""" > testfield/credentials.py

echo """
DB_PREFIX = '$USER'
SRV_ADDRESS = '%s.rb.unifield.org' % DB_PREFIX
# Configuration variables 
XMLRPC_PORT = $XMLRPC_PORT
NETRPC_PORT = $NETRPC_PORT
HTTP_PORT = $WEB_PORT
HTTP_URL_SERVER = 'http://%s:%d' % (SRV_ADDRESS, HTTP_PORT)

# Configuration variable to generate input files / Restore dumps
DB_ADDRESS = '127.0.0.1'
DB_PORT = 12114
DB_USERNAME = 'toto'
DB_PASSWORD = 'toto'

UNIFIELD_ADMIN = 'admin'
UNIFIELD_PASSWORD = 'admin'

SERVER_HWID = ''
USING_DOCKER = False
""" > credentials-msf.py

WEBDIR=/home/$USER/unifield-web
SERVERDIR=/home/$USER/unifield-server

cd testfield
python ${SERVERDIR}/bin/addons/unifield_tests/testfield/init_data/set_rb_partial_tf.py
rm -fr meta_features
rm -fr files
rm -fr output/*

cp -a ${SERVERDIR}/bin/addons/unifield_tests/testfield/meta_features/ .
cp -a ${SERVERDIR}/bin/addons/unifield_tests/testfield/files/ .
NAME=`date +%Y%m%d-%H%M`
export TIME_BEFORE_FAILURE=${TIME_BEFORE_FAILURE:-70}
export COUNT=6
export TEST_DESCRIPTION=${TEST_DESCRIPTION:-$NAME}
export TEST_NAME=${TEST_NAME:-$NAME}
export TEST_DATE=`date +%Y/%m/%d`

./runtests_local.sh

WEBVERSION=`bzr revno --tree $WEBDIR`
SERVERVERSION=`bzr revno --tree $SERVERDIR`
TESTVERSION=`git rev-parse HEAD`
METAVERSION=`find features/ -name '*.feature' -exec md5sum {} \; | md5sum`
echo "S${SERVERVERSION} W${WEBVERSION} M${METAVERSION:0:10} T${TESTVERSION:0:10}" > output/version

DIREXPORT=website/tests/$NAME
mkdir -p "$DIREXPORT"
mv output/* $DIREXPORT
