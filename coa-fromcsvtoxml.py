# -*- encoding: utf-8 -*-
import csv

out = '/tmp/add.xml'
inf = '/tmp/mch.csv'
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
    'tax': 'vat_management.account_type_tax',
    'expense (no p&l)': 'account.account_type_expense_no_pl',
}

ttype = {
    'regular': 'other'
}

type_for_register = [('none', 'None'), ('transfer', 'Transfer'), ('transfer_same','Transfer (same currency)'), ('advance', 'Cash Advance'), ('none', 'Donation'), ('down_payment','Down payment'), ('payroll', 'Third party required - Payroll')]

# column_number: xml_id
destination_xml_id = {
    8: 'analytic_distribution.analytic_account_destination_expatriates',
    9: 'analytic_distribution.analytic_account_destination_national_staff',
    10: 'analytic_distribution.analytic_account_destination_operation',
    11: 'analytic_distribution.analytic_account_destination_support',
}

type_for_reg_dic ={}
for a,b in type_for_register:
    type_for_reg_dic[b.lower()] = a

def toxml(val):
    return val.replace('&', '&amp;').replace('<','&lt;').replace('>','&gt;')

for row in reader:
    if i == 0:
        i += 1
        continue
    destination_string = ''
    destinations = []
    for i in range(8, 12):
        if row[i]:
            if row[i].lower() == 'default':
                destination_string = """\n%s<field name="default_destination_id" ref="%s"/>"""%(' '*12, destination_xml_id[i])
            destinations.append("ref('%s')"%(destination_xml_id[i],))
    if destinations:
        destination_string += """\n%s<field name="destination_ids" eval="[(6, 0, [%s])]"/>"""%(' '*12,', '.join(destinations))

    fo.write('''
        <record model="account.account" id="msf_chart_of_account.%(code)s">
            <field name="code">%(code)s</field>
            <field name="type_for_register">%(third_party)s</field>
            <field name="type">%(type)s</field>
            <field name="name">%(name)s</field>
            <field name="parent_id" %(parent_id)s />
            <field name="reconcile" eval="%(reconcile)s" />
            <field name="user_type" ref="%(user_type)s" />
            <field name="accrual_account" eval="%(accrual)s" />%(destination_string)s
        </record>
'''% {
            'code': row[0],
            'third_party': type_for_reg_dic[row[5].lower()],
            'type': ttype.get(row[3].lower(), row[3].lower()),
            'name': toxml(row[1].strip()),
            'parent_id': row[2] and 'ref="msf_chart_of_account.%s"'%row[2] or '',
            'reconcile': row[6] in ('VRAI', 'True') and 'True' or 'False',
            'user_type': acctype[row[4].lower()],
            'accrual': row[7] in ('VRAI', 'True') and 'True' or 'False',
            'destination_string': destination_string,
        })

fo.write('''    </data>
</openerp>''')
fo.close()
