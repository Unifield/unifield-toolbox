#encoding=utf-8

from oerplib import OERP

SYNC_SERVER_DB_NAME = 'fm-us-1719_SYNC_SERVER'
XMLRPC_PORT = 14703
ADMIN_PWD = 'admin'
PRINT_LIST = True

oerp = OERP(server='localhost', database=SYNC_SERVER_DB_NAME,
                protocol='xmlrpc', port=XMLRPC_PORT)
u = oerp.login('admin', ADMIN_PWD)

model_field_dict = {}

# search for model of sync_server.sync_rule
rule_module = oerp.get('sync_server.sync_rule')
obj_ids = rule_module.search([('active', '=', True)])
for obj in rule_module.read(obj_ids, ['model_id', 'included_fields']):
    if obj['model_id'] not in model_field_dict:
        model_field_dict[obj['model_id']] = set()
    model_field_dict[obj['model_id']].update(eval(obj['included_fields']))

# search for model of sync_server.message_rule
rule_module = oerp.get('sync_server.message_rule')
obj_ids = rule_module.search([('active', '=', True)])
for obj in rule_module.read(obj_ids, ['model_id', 'arguments']):
    if obj['model_id'] not in model_field_dict:
        model_field_dict[obj['model_id']] = set()
    model_field_dict[obj['model_id']].update(eval(obj['arguments']))

model_set = set(model_field_dict.keys())
model_field_dict2 = {}
fields_get_dict = {}

# for each field corresponding to each model, check if it is a m2m m2o or o2m
# if yes, add the model of the relation to the model set

for model, field_list in model_field_dict.items():
    field_list_to_parse = [x for x in field_list if '/id' in x]
    if not field_list_to_parse:
        continue

    if model not in fields_get_dict:
        fields_get_dict[model] = oerp.get(model).fields_get()
    field_get = fields_get_dict[model]

    for field in field_list_to_parse:
        field = field.replace('/id', '')
        if len(field.split('/')) == 2:
            related_field, field = field.split('/')
            related_model = field_get[related_field]['relation']
            if related_model not in model_field_dict2:
                model_field_dict2[related_model] = set()
            model_field_dict2[related_model].add(field)
        elif field_get[field]['type'] in ('many2one', 'many2many', 'one2many'):
            model_set.add(field_get[field]['relation'])

for model, field_list in model_field_dict2.items():
    if model not in fields_get_dict:
        fields_get_dict[model] = oerp.get(model).fields_get()
    field_get = fields_get_dict[model]
    for field in field_list:
        if field_get[field]['type'] in ('many2one', 'many2many', 'one2many'):
            model_set.add(field_get[field]['relation'])

if PRINT_LIST:
    list_to_print = 'WHITE_LIST_MODEL = [\n  '
    model_set = sorted(list(model_set))
    model_list_str = ["'%s'" % x for x in model_set]
    list_to_print += ',\n  '.join(model_list_str)
    list_to_print += '\n]'
    print list_to_print


print '%s models in the list' % len(model_set)


