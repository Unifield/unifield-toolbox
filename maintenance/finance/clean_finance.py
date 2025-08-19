#! /usr/bin/python
  
import psycopg2
import sys

if len(sys.argv) != 2:
    print('%s db_name' % sys.argv[0])
    sys.exit(0)

dsn='dbname=%s' % sys.argv[1]
db = psycopg2.connect(dsn)
cr = db.cursor()



def get_referenced(cr, table, column='id'):
    cr.execute("""
        SELECT tc.table_name, kcu.column_name, ref.delete_rule
        FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu ON ccu.constraint_name = tc.constraint_name
            JOIN information_schema.referential_constraints AS ref ON ref.constraint_name = tc.constraint_name
        WHERE
            tc.constraint_type = 'FOREIGN KEY' AND
            ccu.table_name=%s AND
            ccu.column_name=%s
    """, (table, column))
    return cr.fetchall()


def index_exists(cr, table, column):
    cr.execute("""
select
    t.relname as table_name,
    i.relname as index_name,
    a.attname as column_name
from
    pg_class t,
    pg_class i,
    pg_index ix,
    pg_attribute a
where
    t.oid = ix.indrelid
    and i.oid = ix.indexrelid
    and a.attrelid = t.oid
    and a.attnum = ANY(ix.indkey)
    and t.relkind = 'r'
    and t.relname = %s
    and a.attname = %s
""", (table, column))
    return cr.rowcount


to_del = [
    'account_bank_statement_line',
    'account_bank_statement_line_deleted',
    'account_bank_statement',
    'account_analytic_line',
    'account_invoice_line',
    'account_invoice',
    'account_commitment_line',
    'account_commitment',
    'hr_payroll_msf',
    'hq_entries',
    'msf_budget_line',
    'account_move_unreconcile',
    'account_cashbox_line',
    'account_subscription_line',
    'account_subscription',
    'account_model',
    'cash_request',
    'financing_contract_contract',
    'financing_contract_donor',
    'msf_accrual_line_expense',
    'msf_accrual_line',
    'product_asset_event',
    'product_asset_line',
    'product_asset',
    'msf_budget',
    'deleted_object',
    'ir_attachment',
    'account_move_line',
    'account_move',
    'hr_employee',
    'res_log',
    'deleted_object',
    'ir_attachment',
    'signature_image',
]




new_indexes = []
for table in to_del:
    for other_table, column, b in get_referenced(cr, table):

        if not index_exists(cr, other_table, column):
            index_name = '%s_%s_idx' % (other_table, column)
            new_indexes.append(index_name)
            cr.execute('create index ' + index_name + ' on ' + other_table + ' (' + column + ' )')

print('analyze')
cr.execute('analyze')
print('end analyze')

for table in to_del:
    print('delete ' + table)
    cr.execute('delete from ' + table)

print('End delete')
cr.execute('update sync_client_version set patch=NULL')
cr.execute("delete from audittrail_log_sequence where model='account.move'")
if not index_exists(cr, 'audittrail_log_sequence', 'sequence'):
    cr.execute("create index audittrail_log_sequence_sequence on audittrail_log_sequence(sequence)")
cr.execute("delete from audittrail_log_line where object_id in (select m.id from  ir_model m where m.model in %s)", (tuple([x.replace('_', '.') for x in to_del]), ))
cr.execute("delete from ir_model_data where model in %s", (tuple([x.replace('_', '.') for x in to_del]), ))
db.commit()
for x in new_indexes:
    cr.execute('drop index '+x)

