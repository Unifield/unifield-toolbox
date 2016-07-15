#! /bin/bash

usage() {
cat << EOF
  $0 <from_tree> <to_tree> <destination_diff> [tag_name]
EOF
}
if [ -z "$1" -o ! -d "$1" ];then
    usage
    echo "$1 (from_tree) does not exist"
    exit 1
fi

if [ -z "$2" -o ! -d "$2" ];then
    usage
    echo "$2 (to_tree) does not exist"
    exit 1
fi

if [ -z "$3" -o -d "$3" ];then
    usage
    echo "$3 destination_diff exists"
    exit 1
fi
mkdir $3

TAGNAME=""
if [ ! -z "$4" ]; then
    TAGNAME=$4
fi

TMP="/tmp/$$"
if [ -f ${TMP} ]; then
    echo "$TMP exists, abording ..."
    exit 1
fi

TO_EXCLUDE="unifield-server/tools"
for exclude in ${TO_EXCLUDE}; do
    rm -fr ${1}/${exclude} ${2}/${exclude}
done

# important: set the lang to C or diffstat failed
LANG=C diff --exclude='.bzr' -r $1 $2 | diffstat -p0 -l > $TMP

MISSING=0
SRC=${1%%/}/unifield-server/bin/
DEST=${2%%/}/unifield-server/bin/

WEBSRC=${1%%/}/unifield-web/
WEBDST=${2%%/}/unifield-web/

PATCH_DIR=`readlink -f $3`
WEB_PATCH=${PATCH_DIR}/web/

while read ff; do
    if [[ "${ff}" == ${SRC}* ]]; then
        # if the diff is in from_tree => file remove
        # copy the file, and empty it
        # TODO: missing dir
        let MISSING=${MISSING}+1
        echo "Missing: ${ff##$SRC}"
        cd $SRC
        cp --parents ${ff##$SRC} ${PATCH_DIR}
        cd - >> /dev/null
        echo >  $PATCH_DIR/${ff##$SRC}
    elif [[ "${ff}" == ${DEST}* ]]; then
        cd $DEST
        if [[ "${ff##$DEST}" == "openerp-server.py" ]]; then
            echo "************** WARNING openerp-server.py modified ****************"
            echo "******* openerp-server.exe must be included in the patch file *****"
        fi
        cp -a --parents ${ff##$DEST} ${PATCH_DIR}
        cd - >> /dev/null
    elif [[ "${ff}" == ${WEBDST}* ]]; then
        mkdir -p ${WEB_PATCH}
        cd ${WEBDST}
        cp -a --parents ${ff##$WEBDST} ${WEB_PATCH}
        cd - >> /dev/null
    else
        echo "Mayday, the script has a bug"
        echo "$ff ${DEST} ${SRC} $WEBSRC $WEBDST"
        exit 1
    fi
done < $TMP
echo "$MISSING missing files"
echo "Copy release.py"
cp $DEST/release.py $PATCH_DIR

if [ -e "$PATCH_DIR/unifield-version.txt" ]; then
    echo "unifield-version.txt deleted from patch"
    rm -f $PATCH_DIR/unifield-version.txt
fi

if [ -e "$PATCH_DIR/web/doc/openerp-web-win.cfg" ]; then
    # Win config file is in conf dir
    mkdir $PATCH_DIR/web/conf
    cp $PATCH_DIR/web/doc/openerp-web-win.cfg $PATCH_DIR/web/conf/openerp-web.cfg
fi

if [ -n "$TAGNAME" ]; then
    VERSION="\"$TAGNAME-`date +%Y%m%d-%H%M%S`\""
    echo "Set version $VERSION in release.py"
    echo "version = $VERSION" >> $PATCH_DIR/release.py
    zipfile=`basename $PATCH_DIR`.zip
    if [ ! -e "$zipfile" ]; then
        cd $PATCH_DIR
        zip -qr ../$zipfile .
        md5sum ../$zipfile
    fi
else
    echo "Do not forget do edit release.py"
fi
echo "Do not forget to commit unifield-version.txt"
