# -*- encoding: utf-8 -*-
import csv

out = '/tmp/add.xml'
inf = '/tmp/add.csv'
fo = open(out, 'w')

reader = csv.reader(open(inf, "rb"),delimiter=";",lineterminator="\r",quotechar='"')
i=0
fo.write("""<openerp>
    <data noupdate="1">""")

acctype = {
    'view': 'account.account_type_root',
    'capital': 'account_activable.account_type_capital',
    'asset': 'account.account_type_asset',
    'receivables': 'account.account_type_receivable', 
    'payables': 'account.account_type_payable',
    'liability': 'account.account_type_liability',
    'debt': 'account_activable.account_type_debt',
    'cash': 'account.account_type_cash_moves',
    'expense': 'account.account_type_expense',
    'income': 'account.account_type_income',
    'stock': 'account_activable.account_type_stock',
    'equity': 'account.account_type_cash_equity',
}

ttype = {
    'regular': 'other'
}

type_for_register = [('none', 'None'), ('transfer', 'Transfer'), ('transfer_same','Transfer (same currency)'), ('advance', 'Cash Advance')]
type_for_reg_dic ={}
for a,b in type_for_register:
    type_for_reg_dic[b.lower()] = a

def toxml(val):
    return val.replace('&', '&amp;').replace('<','&lt;').replace('>','&gt;')

for row in reader:
    if i == 0:
        i += 1
        continue
    fo.write('''
        <record model="account.account" id="msf_chart_of_account.%s">
            <field name="code">%s</field>
            <field name="type_for_register">%s</field>
            <field name="type">%s</field>
            <field name="name">%s</field>
            <field name="parent_id" %s />
            <field name="reconcile" eval="%s" />
            <field name="user_type" ref="%s" />
        </record>
'''%(row[0], row[0], type_for_reg_dic[row[5].lower()], ttype.get(row[3].lower(), row[3].lower()), toxml(row[1]), row[2] and 'ref="msf_chart_of_account.%s"'%row[2] or '', row[6] == 'VRAI' and 'True' or 'False', acctype[row[4].lower()] ))

fo.write('''    </data>
</openerp>''')
fo.close()
