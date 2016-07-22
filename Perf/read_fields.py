import oerplib
import time
import csv
import sys

host = '127.0.0.1'
dbname='OCG_NE1_COO_1807_2102'
protocol='netrpc'
port=8070

login='admin'
pwd='admin'
o = oerplib.OERP(host, database=dbname, protocol=protocol, port=port, timeout=100)
u = o.login(login, pwd, dbname)
model_obj = o.get('ir.model')
model_ids = model_obj.search([])
model_names = model_obj.read(model_ids, ['model', 'osv_memory'])
to_read = {}
file_w = open('/tmp/perf.csv', 'w')
error_w = open('/tmp/error.txt', 'w')
c = csv.writer(file_w, delimiter=';', quoting=csv.QUOTE_ALL)

c.writerow(['Method', 'Model', 'Field', 'Time (in s.)'])
model_id = {}

def log_error(string, exception=False):
    if exception:
        string += "\n"
    if isinstance(exception, oerplib.error.RPCError):
        for arg in exception.args:
            string += "%s\n" % arg
    elif exception:
        string += "%s" % exception.message
    print string
    error_w.write(string+"\n")

#print o.get('stock.move').fields_get()
#sys.exit(0)
"""try:
    mo = o.get('stock.move')
    mo.read([1, 2], ['to_be_sent'], {})
except Exception, e:
    log_error('iiiii', e)
    print 'hhhh'
    error_w.close()
    raise
    sys.exit(0)
"""
for model in model_names:
    if model['osv_memory']:
        continue
    try:
        mo = o.get(model['model'])
        a = time.time()
        m_ids = mo.search([], 0, 10)
        c.writerow(['search', model['model'], '', time.time() - a])
    except:
        log_error('Model error: %s' % (model['model'], ))
        continue
    model_id[model['model']] = model['id']
    if m_ids:
        to_read[model['model']] = m_ids

for m in to_read:
    mo = o.get(m)
    a = time.time()
    try:
        mo.read(to_read[m], [], {})
    except Exception, e:
        log_error("Error read %s" % (m, ), e)
        continue
    c.writerow(['read', m, '', time.time() - a])

field_obj = o.get('ir.model.fields')
for m in to_read:
    mo = o.get(m)
    fields_get = mo.fields_get()
    for field in fields_get.keys():
        if fields_get[field].get('func_method'):
            a = time.time()
            try:
                mo.read(to_read[m], [field], {})
            except Exception, e:
                log_error("Read field error %s %s" % (m, field) ,e)
                continue
            c.writerow(['read field', m, field, time.time() - a])

file_w.close()
error_w.close()
