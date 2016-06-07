#! /bin/bash

if [ -z "$1" ]; then
	echo $0 instance
	exit 1
fi

mkdir -p /home/$1/archive
/etc/init.d/$1-server stop
/etc/init.d/$1-web stop
update-rc.d -f $1-server remove
update-rc.d -f $1-web remove
cp /etc/apache2/sites-enabled/$1 /home/$1/etc/apache_config

rm /etc/apache2/sites-enabled/$1
/etc/init.d/apache2 reload
for i in  `psql -t -d template1 -c "SELECT d.datname FROM pg_catalog.pg_database d WHERE pg_get_userbyid(d.datdba) = '$1';"`; do 
echo "Dump $i"
pg_dump -Fc $i > /home/$1/archive/$i
dropdb $i
done
