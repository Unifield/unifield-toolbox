#! /bin/bash
usage()
{
    cat << EOF
usage: $0 options [name]

This script set a UniField windows source tree

OPTIONS:
-h          This help msg
-s <serie>  Launchpad serie to retrieve (default trunk)
-t <tag>    Tag name
<directory> Directory
EOF
}

TAG=""
BZRBRANCH=""
SYNCBZRBRANCH=""
while getopts "hs:t:" OPTION
do
    case $OPTION in
        h)
            usage
            exit 1
            ;;
        t)
           TAG="-r $OPTARG"
           ;;
        s)
           BZRBRANCH="/$OPTARG"
           SYNCBZRBRANCH="-$OPTARG"
           ;;
        ?)
           usage
           exit 0
           ;;
    esac
done

shift $(($OPTIND - 1))
if [ -z "$1" ]; then
    usage
    exit 1
fi

if [ -f "$1" -o -d "$1" ]; then
    echo "Directory $1 exists"
    exit 1
fi

mkdir $1
cd $1

echo "== web =="
echo bzr branch $TAG lp:unifield-web/${BZRBRANCH} unifield-web
bzr branch $TAG lp:unifield-web/${BZRBRANCH} unifield-web

echo "== server =="
echo bzr branch $TAG lp:unifield-server${BZRBRANCH} unifield-server
bzr branch $TAG lp:unifield-server${BZRBRANCH} unifield-server
cd unifield-server/bin/addons

#echo "== addons =="
#echo bzr branch $TAG lp:unifield-addons${BZRBRANCH} unifield-addons
#bzr branch $TAG lp:unifield-addons${BZRBRANCH} unifield-addons
#mv unifield-addons/* .
#rm -fr unifield-addons

#echo "== wm =="
#echo bzr branch $TAG lp:unifield-wm${BZRBRANCH} unifield-wm
#bzr branch $TAG lp:unifield-wm${BZRBRANCH} unifield-wm
#mv unifield-wm/* .
#rm -fr unifield-wm

#echo "== sync_module =="
#echo bzr branch $TAG lp:unifield-wm/sync${SYNCBZRBRANCH} sync_module_prod
#bzr branch $TAG lp:unifield-wm/sync${SYNCBZRBRANCH} sync_module_prod
#mv sync_module_prod/* .
#rm -fr sync_module_prod
