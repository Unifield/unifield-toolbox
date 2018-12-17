from oerplib import OERP

server_ip = '127.0.0.1'
xmlrcp_port = '10081'

db = "prod_OCG_HQ_20181215_1300"

user = 'admin'
password = ''

oerp = OERP(server=server_ip, protocol='netrpc', port=xmlrcp_port, timeout=3600, version='6.0')
oerp.login(user, password, db)

prod_o = oerp.get('product.product')

rate = 0.8827
print "BEGIN;"
print "update product_product set currency_id=5, field_currency_id=5 where international_status=6 and currency_id=1;"

to_compute_ids = prod_o.search([('international_status', '=', 6), ('currency_id', '=', 1) , ('standard_price', '!=', 1)])
for x in prod_o.read(to_compute_ids, ['standard_price', 'product_tmpl_id', 'default_code']):
    newprice = round(x['standard_price'] / rate, 5)
    print "--- %s %s EUR to %s CHF"%(x['default_code'], x['standard_price'], newprice)
    print "update product_product set currency_id=5, field_currency_id=5 where id=%s;" % (x['id'], )
    print "update product_template set standard_price=%s, list_price=%s where id=%s;" % (newprice, newprice, x['product_tmpl_id'][0])
    print "insert into standard_price_track_changes ( create_uid, create_date, old_standard_price, new_standard_price, user_id, product_id, change_date, transaction_name) values (1, NOW(), %s, %s, 1, %s, date_trunc('second', now()::timestamp), 'DataFix US-5429');" % (x['standard_price'], newprice, x['id'])


print "ROLLBACK;"
