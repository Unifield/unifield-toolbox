#! /bin/bash

if [ -z "$1" ]; then
    echo $0 instance
    exit 1
fi

/etc/init.d/$1-server stop
/etc/init.d/$1-web stop
update-rc.d -f $1-server remove
update-rc.d -f $1-web remove
cp /etc/apache2/sites-enabled/$1 /home/$1/etc/apache_config
rm /etc/apache2/sites-enabled/$1
/etc/init.d/apache2 reload
#for i in `find /etc/apache2/sites-enabled/ -name "*-$1" -type l`; do
#   echo $i
#   rm $i
#done
