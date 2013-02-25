#! /bin/bash

if [ -z "$1" -o ! -d "$1" ];then
    echo "$0 from_tree to_tree destination_diff"
    echo "$1 (from_tree) does not exist"
    exit 1
fi

if [ -z "$2" -o ! -d "$2" ];then
    echo "$0 from_tree to_tree destination_diff"
    echo "$2 (to_tree) does not exist"
    exit 1
fi

if [ -z "$3" -o -d "$3" ];then
    echo "$0 from_tree to_tree destination_diff"
    echo "$3 destination_diff exists"
    exit 1
fi
mkdir $3

TMP="/tmp/$$"
if [ -f ${TMP} ]; then
    echo "$TMP exists, abording ..."
    exit 1
fi

# important: set the lang to C or diffstat failed
LANG=C diff --exclude='.bzr' -r $1 $2 | diffstat -p0 -l > $TMP

MISSING=0
SRC=${1%%/}/unifield-server/bin/
DEST=${2%%/}/unifield-server/bin/
PATCH_DIR=`readlink -f $3`
while read ff; do
    if [[ "${ff}" == ${SRC}* ]]; then
        # if the diff is in from_tree => file remove
        # copy the file, and empty it
        # TODO: missing dir
        let MISSING=${MISSING}+1
        cd $SRC
        cp --parents ${ff##$SRC} ${PATCH_DIR}
        cd - >> /dev/null
        echo >  $PATCH_DIR/${ff##$SRC}
    elif [[ "${ff}" == ${DEST}* ]]; then
        cd $DEST
        cp -a --parents ${ff##$DEST} ${PATCH_DIR}
        cd - >> /dev/null
    else
        echo "Mayday, the script has a bug"
        echo $ff
        exit 1
    fi
done < $TMP
echo "$MISSING missing files"
