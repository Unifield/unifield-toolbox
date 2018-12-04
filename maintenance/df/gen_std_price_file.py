from oerplib import OERP
import csv
import sys
import cStringIO
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

server_ip = '127.0.0.1'
xmlrcp_port = '10083'
db = 'prod_OCG_HQ_20181128_1300'
user = 'admin'
password = ''
crypt_pass = ''
out_file = 'out.csv'
rate = 1.13

class crypt():
    def __init__(self, password):
        password = bytes(password)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            iterations=100000,
            salt=password,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        self.Fernet = Fernet(key)

    def encrypt(self, string):
        return self.Fernet.encrypt(string)

    def decrypt(self, string):
        return self.Fernet.decrypt(bytes(string))

oerp = OERP(server=server_ip, protocol='xmlrpc', port=xmlrcp_port, timeout=3600, version='6.0')
oerp.login(user, password, db)


prod_o = oerp.get('product.product')
model_data_o = oerp.get('ir.model.data')
csv_out = cStringIO.StringIO()
writer = csv.writer(csv_out, delimiter=',', quoting=csv.QUOTE_ALL)

file_in = open(sys.argv[1], 'r')
reader = csv.reader(file_in, delimiter=',', quoting=csv.QUOTE_ALL)

reader.next()
writer.writerow(['product_code', 'sdref', 'new_price'])

data = {}
prod = {}
xmlid = {}
for x in reader:
    data[x[0]] = x[2].replace(',', '.')

p_ids = prod_o.search([('default_code', 'in', data.keys()), ('active', 'in', ['t', 'f'])])
for p in prod_o.read(p_ids, ['default_code']):
    prod[p['default_code']] = p['id']

data_ids = model_data_o.search([('model', '=', 'product.product'), ('module', '=', 'sd'), ('res_id', 'in', p_ids)])
for p in model_data_o.read(data_ids, ['name', 'res_id']):
    xmlid[p['res_id']] = p['name']


for def_code in sorted(data.keys()):
    try:
        writer.writerow([def_code, xmlid[prod[def_code]], round(float(data[def_code])*rate, 5)])
    except Exception, e:
        print e
        print def_code

content = csv_out.getvalue()
c = crypt(crypt_pass)
f = open(out_file, 'wb')
f.write(c.encrypt(content))
