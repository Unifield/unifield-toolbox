#!/bin/bash

if [ -z "$1" ]
then
    echo "No runbot name supplied";
    echo "Usage:";
    echo "    sh update_dir.sh runbot";
    exit 1;
fi

runbot=$1

echo "Creation of the update_dir.sh script on the runbot home"
echo "#!/bin/bash

runbot=$USER

# Stop web and server
/etc/init.d/$runbot-server stop
/etc/init.d/$runbot-web stop

# Update code directories
cd /home/$runbot/unifield-wm;
bzr pull;
cd /home/$runbot/unifield-server;
bzr pull;
cd /home/$runbot/unifield-addons;
bzr pull;
cd /home/$runbot/unifield-web;
bzr pull;
cd /home/$runbot/sync_module_prod;
bzr pull;
cd /home/$runbot/sync_env_script;
bzr pull;
cd /home/$runbot;

# Restart web and server
/etc/init.d/$runbot-server start
/etc/init.d/$runbot-web start

# Re-generate DB
python /home/$runbot/sync_env_script/mkdb.py

# Run last sync.
python /home/$runbot/sync_env_script/run_last_sync.py" | ssh root@uf0003.unifield.org "su $runbot -c 'cat > /home/$runbot/update_dir.sh'"


echo "Run the update of the runbot over SSH"
ssh root@uf0003.unifield.org "su $runbot -c 'sh /home/$runbot/update_dir.sh > /home/$runbot/update_dir.log' &"
