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
sync_user_admin = True
default_email = 'null@msf.org'
company_name = 'Médecins Sans Frontières'
lang = @@MKDB_LANG@@ # fr_MF or es_MF
default_oc = 'oca'
default_currency = '@@MKDB_CURR@@' # 'chf' or 'eur'
# or describe custom currency for HQs here (override default_currency above):
currency_tree = {
    'HQ1': '@@MKDB_CURR@@',
    'HQ2': 'chf',
}
if currency_tree['HQ1'] == 'chf':
    currency_tree['HQ2'] = 'eur'
else:
    currency_tree['HQ2'] = 'chf'

# WARNING:
# hq_count = h, coordo_count = c, project_count = p 
# will create
# h hq instance, 
# (c*h) coordo, 
# and (p*c*h) projects !
hq_count = @@NUM_HQ@@
coordo_count = @@NUM_COORDO@@
project_count = @@NUM_PROJECT@@
# or describe the instances with instance_tree
@@FULL_TREE@@
instance_tree = {
    'HQ1': {
        'C1': ['P1', 'P2'],
        'C2': ['P1'],
    },
    'HQ2': {
        'C1': [],
    },
}
@@FULL_TREE@@

@@INTERMISSION_TREE@@
instance_tree = {
    'HQ1': {
        'C1': ['P1'],
        'C2': ['P1'],
    },
}
@@INTERMISSION_TREE@@

@@INTERSECTION_TREE@@
instance_tree = {
    'HQ1': {
        'C1': ['P1'],
        'C2': ['P1'],
    },
    'HQ2': {
        'C1': [],
    },
}
@@INTERSECTION_TREE@@

load_test = 1250
source_path = '/home/@@USERERP@@'
addons = [@@ADDONSDIR@@]
server_restart_cmd = '/etc/init.d/@@USERERP@@-server restart'
web_restart_cmd = '/etc/init.d/@@USERERP@@-web restart'
dump_dir = '/home/@@USERERP@@/exports'

# uncomment the next 3 parameters to load UserRights
@@COMMENT_ACL@@
load_uac_file = '/home/@@USERERP@@/unifield-server/bin/addons/msf_profile/user_rights/uac.xml'
#load_users_file = '/home/@@USERERP@@/sync_env_script/data/unifield_users.csv'
load_extra_files = [
    '/home/@@USERERP@@/unifield-server/bin/addons/msf_profile/user_rights/ir.actions.act_window.csv',
    '/home/@@USERERP@@/unifield-server/bin/addons/msf_profile/user_rights/ir.model.access.csv',
    '/home/@@USERERP@@/unifield-server/bin/addons/msf_profile/user_rights/ir.rule.csv',
    '/home/@@USERERP@@/unifield-server/bin/addons/msf_profile/user_rights/msf_field_access_rights.field_access_rule.csv',
    '/home/@@USERERP@@/unifield-server/bin/addons/msf_profile/user_rights/msf_field_access_rights.field_access_rule_line.csv',
    '/home/@@USERERP@@/unifield-server/bin/addons/msf_profile/user_rights/msf_button_access_rights.button_access_rule.csv',
    '/home/@@USERERP@@/sync_env_script/data/master_hq/product.product.csv',
]
@@COMMENT_ACL@@
