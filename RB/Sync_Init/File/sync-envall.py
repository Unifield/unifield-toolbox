# -*- coding: utf-8 -*-

## Postgres admin password
db_password = '@@ADMINDBPASS@@'
## admin password
admin_password = '@@WEB_ADMIN_PASS@@'
## User login & password
user_login = '@@WEB_LOGIN_USER@@'
user_password = '@@WEB_LOGIN_PASS@@'

## Infos to connect to server (sync client side)
client_host = 'localhost' #'10.42.43.1'
client_port = @@XMLRPCPORT@@

## Infos to connect to server (sync server side)
server_host = 'localhost' #'10.42.43.1'
server_port = @@XMLRPCPORT@@
netrpc_port = @@NETRPCPORT@@

## Database format
prefix = "@@DBNAME@@"


## Other stuffs
sync_user_admin = False
default_email = 'null@msf.org'
company_name = 'Médecins Sans Frontières'
currency = 'eur' # or chf
lang = False # fr_MF or es_MF

# WARNING:
# hq_count = h, coordo_count = c, project_count = p 
# will create
# h hq instance, 
# (c*h) coordo, 
# and (p*c*h) projects !
hq_count = 1
coordo_count = 1
project_count = @@NUM_PROJECT@@

load_test = 1250
source_path = '/home/@@USERERP@@'
addons = [@@ADDONSDIR@@]
server_restart_cmd = '/etc/init.d/@@USERERP@@-server restart'
web_restart_cmd = '/etc/init.d/@@USERERP@@-web restart'
dump_dir = '/home/@@USERERP@@/exports'

# uncomment the next 3 parameters to load UserRights
#load_uac_file = 'data/uac.xml'
#load_users_file = 'data/unifield_users.csv'
#load_extra_files = [
#    'data/extra/ir.actions.act_window.csv',
#    'data/extra/ir.model.access.csv',
#    'data/extra/ir.rule.csv',
#    'data/extra/msf_field_access_rights.field_access_rule.csv',
#    'data/extra/msf_field_access_rights.field_access_rule_line.csv',
#    'data/extra/msf_button_access_rights.button_access_rule.csv',
#]

