#! /bin/bash

if [ -z "$1" ]; then
	echo $0 instance
	exit 1
fi

#/etc/init.d/$1-server stop
#/etc/init.d/$1-web stop
ENCRYPT="/etc/letsencrypt"
if [[ -f ~/RBconfig ]]; then
   source ~/RBconfig
fi

if [[ "$1" == "XXus-8546" || "$1" == "jn-us-9463" ]]; then
    echo "Please keep $1 !"
    exit 1
fi
#update-rc.d -f $1-server remove
#update-rc.d -f $1-web remove
systemctl stop $1-server
systemctl stop $1-web
killall -u $1
killall -s 9 -u $1
a2dissite ${1}.conf
[[ -f /etc/apache2/sites-enabled/$1 ]] && rm /etc/apache2/sites-enabled/$1
/etc/init.d/apache2 reload
for i in  `${PG_PATH}psql -t -d template1 -c "SELECT d.datname FROM pg_catalog.pg_database d WHERE pg_get_userbyid(d.datdba) = '$1';"`; do 
echo "Dropdb $i"
${PG_PATH}dropdb $i
done

export PGCLUSTER=14/main
for i in  `psql -t -d template1 -c "SELECT d.datname FROM pg_catalog.pg_database d WHERE pg_get_userbyid(d.datdba) = '$1';"`; do 
echo "Dropdb $i"
dropdb $i
done

systemctl disable $1-server
systemctl disable $1-web
rm /etc/systemd/system/$1-server.service
rm /etc/systemd/system/$1-web.service
systemctl daemon-reload

rm -f /etc/sudoers.d/99-$1

fullname="${1}.${rb_server_url}"
if [ -f ${ENCRYPT}/renewal/${fullname}.conf ]; then
    rm -fr ${ENCRYPT}/renewal/${fullname}.conf
fi
if [ -d ${ENCRYPT}/archive/${fullname} ]; then
    rm -fr ${ENCRYPT}/archive/${fullname}
fi
if [ -d ${ENCRYPT}/live/${fullname} ]; then
    rm -fr ${ENCRYPT}/live/${fullname}
fi

userdel -r $1
