#! /bin/bash

if [ -z "$1" ]; then
	echo $0 instance
	exit 1
fi

/etc/init.d/$1-server stop
/etc/init.d/$1-web stop
update-rc.d -f $1-server remove
update-rc.d -f $1-web remove
killall -u $1
killall -s 9 -u $1
rm /etc/apache2/sites-enabled/$1
/etc/init.d/apache2 reload
for i in  `psql -t -d template1 -c "SELECT d.datname FROM pg_catalog.pg_database d WHERE pg_get_userbyid(d.datdba) = '$1';"`; do 
echo "Dropdb $i"
dropdb $i
done
userdel -r $1
