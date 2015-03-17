# -*- coding: utf-8 -*-
from random import randrange, choice, randint
from time import strftime
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import os
import csv

from chrono import TestChrono


TEST_MODES = (
    'unit',  # one entry for each register/ccy in first period
    'period',  # one entry for each register/ccy in all periods
    'fake',  # process virtually flow iterations, no entry generated
    'full_1st_period',  # full process of the first period (Jan of first FY)
)
TEST_MODE = False

MASK = {
    'register': "%s %s",
    'register_line': "reg l %s",
    'je': "JE %s",
    'ji': "JI %s",
    'ad': "AD %s",
    'cheque_number': "cheque %s",
}


class FinanceFlowException(Exception):
    pass
    
    
class FinanceFlowBase(object):
    def __init__(self, proxy):
        self.proxy = proxy
        self.cache_clear()
        self._counters = {}
        self._chrono_data = {}
        
    def get_cfg(self, key, default=None):
        return self.proxy.config.get('finance', key, default)
        
    def get_cfg_int(self, key, default=None):
        res = self.proxy.config.getint('finance', key)
        if not res and default is not None:
            res = default
        return res
        
    def cache_clear(self):
        """
        clear cache
        """
        self._cache = {}

    def cache_set(self, key, val):
        """
        store a value in cache
        :param key: key for value
        :param val: valueclea
        :return: value
        """
        self._cache[key] = val
        return val

    def cache_get(self, key):
        """
        get a value from cache
        :param key: key for value to get
        :return:
        """
        return self._cache.get(key, False)
        
    def get_random_amount(self, min=100, max=10000):
        """
        get a random amount
        """
        return randint(min, max)
        
    def chrono_start(self, entry_type, year, month):
        """
        start a chrono for a given 'entry type' for the given period
        :param entry_type: name for the type of entry measured
        :type year: int
        :type month: int
        """
        # '-' is used to delimit entry_type/year/month: replace it by '_'
        entry_type = entry_type.replace('-', '_')  
        name = "%s-%04d-%02d" % (entry_type, year, month, )
        self._chrono_last = TestChrono(name)
        self._chrono_last.start()
    
    def chrono_stop(self):
        """
        measure last started chrono
        """
        if self._chrono_last:
            chrono = self._chrono_last
            chrono.stop()
            
            self._chrono_data.setdefault(chrono.name, {
                'count': 0,
                'elapsed': 0.,
            })
            self._chrono_data[chrono.name].update({
                'count':
                    self._chrono_data[chrono.name]['count'] + 1,
                'elapsed':
                    self._chrono_data[chrono.name]['elapsed'] + \
                        chrono.process_time,
            })
            
            self._chrono_last = False
            
    def chrono_report(self, csv_name, entry_types):
        """
        proceed csv report of elapsed time measures
        :param csv_name: csv name without csv suffix
        :param entry_types: chrono entry types to report
        :type entry_types: list
        """
        res = []
        total = {}
        total_all = {
            'count': 0,
            'elapsed': 0,
        }
        
        def compute_period(et, month, year, name):
            average = self._chrono_data[name]['elapsed'] / \
                self._chrono_data[name]['count']
            res.append([
                "%04d-%02d" % (year, month, ),
                self._chrono_data[name]['count'],
                self._chrono_data[name]['elapsed'] / \
                    self._chrono_data[name]['count'],
            ])
            
            # total / entry type
            total.setdefault(et, {
                'count': 0,
                'elapsed': 0,
                'average': 0,
            })
            total[et].update({
                'count': total[et]['count'] + self._chrono_data[name]['count'],
                'elapsed': total[et]['elapsed'] + \
                    self._chrono_data[name]['elapsed'],
            })
            
            # total / all (no average)
            total_all.update({
                'count': total_all['count'] + self._chrono_data[name]['count'],
                'elapsed': total_all['elapsed'] + \
                    self._chrono_data[name]['elapsed'],
            })
            
        def compute_total_average():
            for et in total:
                total[et]['average'] = total[et]['elapsed'] / \
                    total[et]['count']
                    
        def render():
            report_path = '%s/%s.csv' % (
                os.path.dirname(os.path.abspath(__file__)), csv_name, )
            with open(report_path, 'wb') as csv_file:
                csv_writer = csv.writer(csv_file, delimiter=',',
                    quoting=csv.QUOTE_MINIMAL)
                    
                # results
                for r in res:
                    csv_writer.writerow(r)
                
                # totals
                for x in range(0, 3):
                    csv_writer.writerow([])
                csv_writer.writerow(['TOTALS', 'count', 'elapsed', 'average', ])
                for et in sorted(total.keys()):
                    csv_writer.writerow([
                        et,
                        total[et]['count'],
                        total[et]['elapsed'],
                        total[et]['average'],
                    ])
                csv_writer.writerow([
                    'TOTAL',
                    total_all['count'],
                    total_all['elapsed'],
                ])
            csv_file.close()
        
        # compute results for wanted entry types
        reported_et = []
        for et in entry_types:
            for name in sorted(self._chrono_data.keys()):
                name_prefix = et + '-'
                if name.startswith(et):
                    parts = name.split('-')
                    if parts and len(parts) == 3:
                        et, year, month = parts
                        if et in entry_types:
                            if reported_et and not et in reported_et:
                                # lines separator between entry types
                                for x in range(0, 3):
                                    res.append([])
                            if not et in reported_et:
                                res.append([et, 'count', 'average', ])
                                reported_et.append(et)
                            year = int(year)
                            month = int(month)
                            compute_period(et, month, year, name)
        compute_total_average()
        render()

    def get_partner(self, partner_type):
        """
        get first partner id from type
        :param partner_type: partner type
        :type partner_type: str
        """
        partner_ids = self.proxy.partner.search(
            [('partner_type', '=', partner_type)])
        if not partner_ids:
            raise FinanceFlowException('partner not found')
        return partner_ids[0]
        
    def get_employee(self):
        """
        get first expat employee id
        create a default one if no any employee
        """
        emp_ids = self.proxy.emp.search([('employee_type', '=', 'ex')])
        if emp_ids:
            res = emp_ids[0]
        else:
            # create default employee
            res = self.proxy.emp.create({
                'name': 'Expat Employee',
                'employee_type': 'ex',
            })
            if not res:
                raise FinanceFlowException('can not create default employee')
        return res

    def get_purchase_journal(self):
        """
        get first purchase journal id
        :return: id
        """
        journal_ids = self.proxy.journal.search([('type', '=', 'purchase')])
        if not journal_ids:
            raise FinanceFlowException('purchase journal not found')
        return  journal_ids[0]
        
    def get_account_from_account_type(self, account_type,
        is_analytic_addicted=None):
        """
        get account ids from user account type (code or name)
        code between: asset, capital, cash, debt, equity, expense, income,
        payables, receivables, specific, stock, tax, view
        :param account_type: account user type code or name
        """
        domain = [
            '|',
            ('code', '=', account_type),
            ('name', '=', account_type),
        ]
        acc_type_ids = self.proxy.acc_type.search(domain)
        if not acc_type_ids:
            raise FinanceFlowException("account type '%s' not found" % (
                account_type, ))
        domain = [
            ('type', '!=', 'view'),
            ('user_type', '=', acc_type_ids[0]),
        ]
        if is_analytic_addicted is not None:
            domain += [('is_analytic_addicted', '=', is_analytic_addicted)]
        return self.proxy.acc.search(domain)

    def get_period(self, dt):
        """
        get period id from date
        :type dt: str '%Y-%m-%d'
        :return: id
        """
        period_ids = self.proxy.per.get_period_from_date(dt)
        if not period_ids:
            raise FinanceFlowException("%s period not found" % (dt, ))
        return period_ids[0]
        
    def get_date_for_month(self, month, year, day=1):
        """
        get date in the given month
        :rtype date str for orm
        """
        return "%04d-%02d-%02d" % (year, month, day, )
        
    def get_random_date_for_month(self, month, year):
        """
        get a random date in the given month
        :param month: month number
        :type month: int
        :rtype date str for orm
        """
        rday = randint(1, 30)
        day = 28 if rday > 28 and month == 2 else rday
        return self.get_date_for_month(month, year, day=day)
        
    def get_random_date_for_period(self, period_br):
        """
        get a random date in the given period's month
        :param period_br: browsed period
        :rtype date str for orm
        """
        return self.get_random_date_for_month(period_br.date_start.month,
            period_br.date_start.year)
        
    def create_journal(self, name, code, journal_type,
        analytic_journal_id=False, account_code=False, currency_name=False,
        bank_journal_id=False):
        """
        create journal
        if of type bank/cash/cheque: account_code and currency_name needed.

        :param name: journal name
        :param code: journal code
        :param journal_type: journal type. available types::
         * accrual
         * bank
         * cash
         * cheque
         * correction
         * cur_adj
         * depreciation
         * general
         * hq
         * hr
         * inkind
         * intermission
         * migration
         * extra
         * situation
         * purchase
         * purchase_refund
         * revaluation
         * sale
         * sale_refund
         * stock
        :param analytic_journal_id: (optional) linked analytic journal id
            default attempt to search an analytic journal that have the same
            journal_type
        :param account_code: (mandatory for bank/cash/cheque) account
            code that will be used in debit/credit for the journal
        :param currency_name: (mandatory for bank/cash/cheque) journal
            currency name
        :param bank_journal_id: (mandatory for cheque) linked bank journal
        :return: journal id
        :rtype: int
        """
        # checks
        if not name:
            raise FinanceFlowException("name missing")
        if not code:
            raise FinanceFlowException("code missing")
        if not journal_type:
            raise FinanceFlowException("journal type missing")
        # bank/cash/cheque
        if journal_type in ('bank', 'cheque', 'cash', ):
            if not account_code or not currency_name:
                tpl = "bank/cash/cheque: account code and a currency" \
                      " required. account: '%s', currency: '%s'"
                raise FinanceFlowException(tpl % (account_code or '',
                    currency_name or '', ))
        # cheque journal
        if journal_type == 'cheque' and not bank_journal_id:
            tpl = "bank journal mandatory for cheque journal"
            raise FinanceFlowException(tpl)

        # analytic journal
        if not analytic_journal_id:
            analytic_journal_type = journal_type
            if journal_type in ('bank', 'cheque', ):
                analytic_journal_type = 'cash'
            aaj_ids = self.proxy.ana_journal.search(
                [('type', '=', analytic_journal_type)])
            if not aaj_ids:
                tpl = "no analytic journal found with this type: %s"
                raise FinanceFlowException(tpl % (journal_type, ))
            analytic_journal_id = aaj_ids[0]

        # prepare values
        vals = {
            'name': name,
            'code': code,
            'type': journal_type,
            'analytic_journal_id': analytic_journal_id,
        }
        if account_code:
            a_ids = self.proxy.acc.search([('code', '=', account_code)])
            if not a_ids:
                tpl = "no account found for the given code: %s"
                raise FinanceFlowException(tpl % (account_code, ))
            account_id = a_ids[0]
            vals.update({
                'default_debit_account_id': account_id,
                'default_credit_account_id': account_id,
            })
        if currency_name:
            c_ids = self.proxy.ccy.search([('name', '=', currency_name)])
            if not c_ids:
                tpl = "currency not found: %s"
                raise FinanceFlowException(tpl % (currency_name, ))
            vals.update({'currency': c_ids[0]})
        if bank_journal_id:
            vals['bank_journal_id'] = bank_journal_id
        # create the journal
        return self.proxy.journal.create(vals)
        
    def create_register(self, name, code, register_type, account_code,
        currency_name, bank_journal_id=False):
        """
        create a register in the current period.
        (use create_journal)
        :param name: register name (used as journal's name)
        :param code: register's code (used as journal's code)
        :param register_type: register available types::
         * bank
         * cash
         * cheque
        :param account_code: account code used for debit/credit account
            at journal creation. (so used by the register)
        :param currency_name: name of currency to use(must exists)
        :param bank_journal_id: (mandatory for cheque) linked bank journal
        :return: register_id and journal_id
        :rtype: tuple (registed id, journal id)
        """
        analytic_journal_code_map = {
            'cash': 'CAS',
            'bank': 'BNK',
            'cheque': 'CHK',
        }
        aaj_code = analytic_journal_code_map[register_type]
        aaj_ids = self.proxy.ana_journal.search([('code', '=', aaj_code)])
        if not aaj_ids:
            tpl = "analytic journal code %s not found"
            raise FinanceFlowException(tpl % (aaj_code, ))

        j_id = self.create_journal(name, code, register_type,
            account_code=account_code, currency_name=currency_name,
            bank_journal_id=bank_journal_id,
            analytic_journal_id=aaj_ids[0])
        # search the register (should be created by journal creation)
        reg_ids = self.proxy.reg.search([('journal_id', '=', j_id)])
        return reg_ids and reg_ids[0] or False, j_id
        
    def open_register(self, ids):
        """
        open all registers given by id
        """
        if not ids:
            return
        if isinstance(ids, (int, long)):
            ids = [ids]
        for register in self.proxy.reg.browse(ids):
            if not register.journal_id.type or register.state != 'draft':
                continue
            if register.journal_id.type == 'cash':
                # we dirty skip wizard.open.empty.cashbox
                # reg_obj.button_open_cash([register.id])
                self.proxy.reg.do_button_open_cash([register.id])
            elif register.journal_id.type == 'bank':
                self.proxy.reg.button_open_bank([register.id])
            elif register.journal_id.type == 'cheque':
                self.proxy.reg.button_open_cheque([register.id])
                
    def create_analytic_distribution(self, account_id=False):
        """
        create analytic distribution
        :param account_id: related accountdb._id (if not set search for a random
            destination)
        :type account_id: int
        :return: ad id
        """
        company = self.proxy.comp.browse(self.proxy.comp.search([])[0])
        funding_pool_pf_id = self.proxy.get_record_id_from_xmlid(
            'analytic_distribution', 'analytic_account_msf_private_funds', )
        cost_center_id = False
        funding_pool_id = False

        # DEST/CC/FP
        if not account_id:
            # no account: any DEST, default instance CC and PF funding pool
            destination_ids = self.proxy.ana_acc.search(
                [('category', '=', 'DEST'), ('type', '=', 'normal')])
            cost_center_id = company.instance_id.top_cost_center_id \
                and company.instance_id.top_cost_center_id.id or False
            funding_pool_id = funding_pool_pf_id
        else:
            # random DEST/FP from account via 'account.destination.link'
            # (PF randomly taken too) and compatible CC
            adl_ids = self.proxy.acc_dest_link.search(
                [('account_id', '=', account_id)])
            if adl_ids:
                # random dest from account/dest tuple
                adl_br = self.proxy.acc_dest_link.browse(choice(adl_ids))
                destination_ids = [adl_br.destination_id.id]
                
                # random CC
                cost_center_ids = self.proxy.ana_acc.search(
                    [('category', '=', 'OC'), ('type', '=', 'normal')])
                cost_center_id = choice(cost_center_ids)
                
                # PF FP
                funding_pool_id = funding_pool_pf_id
            else:
                cost_center_id = instance.top_cost_center_id \
                    and instance.top_cost_center_id.id or False
                funding_pool_id = funding_pool_pf_id
                account = self.proxy.acc.browse(account_id)
                destination_ids = account.destination_ids
        if not destination_ids:
            raise FinanceFlowException('no destinations found')
        if not cost_center_id:
            raise FinanceFlowException('no cost center found')
        if not funding_pool_id:
            raise FinanceFlowException('no funding pool found')
        destination_id = choice(destination_ids)
            
        # create ad
        name = MASK['ad'] % (self.proxy.get_uuid(), )
        distrib_id = self.proxy.ad.create({'name': name})
        data = [
            ('cost.center.distribution.line', cost_center_id, False),
            ('funding.pool.distribution.line', funding_pool_id, cost_center_id),
        ]
        for analytic_obj, value, cc_id in data:
            vals = {
                'distribution_id': distrib_id,
                'name': name,
                'analytic_id': value,
                'cost_center_id': cc_id,
                'percentage': 100.0,
                'currency_id': company.currency_id.id,
                'destination_id': destination_id,
            }
            self.proxy.get(analytic_obj).create(vals)
        return distrib_id

    def create_journal_entry(self, booking_ccy_id, year, month, items_count,
        with_ad):
        """
        create a JE (with items_count JI in it (expense and counterpart lines)
        :param with_ad: True if AD should be generated
        :type with_ad: boolean
        """
        entry_date = self.get_random_date_for_month(month, year)

        # purchase journal
        journal_id = self.get_purchase_journal()

        # current period
        period_id = self.get_period(entry_date)

        # partner (external)
        partner_id = self.get_partner('external')

        # create JE
        name = MASK['je'] % (self.proxy.get_uuid(), )
        entry_name = name
        vals = {
            'journal_id': journal_id,
            'period_id': period_id,
            'date': entry_date,
            'document_date': entry_date,
            'partner_id': partner_id,
            'status': 'manu',
            'name': name,
            'manual_name': name,
            'manual_currency_id': booking_ccy_id,
        }
        move_id = self.proxy.am.create(vals)
        if not move_id:
            raise FinanceFlowException('account move creation failed :: %s' % (
                vals, ))

        # create JI
        items_count = items_count / 2  # counter part included
        index = 0
        while index < items_count:
            name = MASK['ji'] % (self.proxy.get_uuid(), )
            random_amount = self.get_random_amount()
            
            if with_ad:
                account_ids = self.cache_get('ji_account_ids_ad')
                if not account_ids:
                    domain = [
                        ('is_analytic_addicted', '=', True),
                        ('type', '=', 'other'),
                        ('code', '>', '6'),
                    ]
                    account_ids = self.proxy.acc.search(domain)
                    self.cache_set('ji_account_ids_ad', account_ids)
            else:
                account_ids = self.cache_get('ji_account_ids')
                if not account_ids:
                    domain = [
                        ('is_analytic_addicted', '!=', True),
                        ('type', '=', 'payable'),
                    ]
                    account_ids = self.proxy.acc.search(domain)
                    self.cache_set('ji_account_ids', account_ids)
            random_account_id = choice(account_ids)
            vals = {
                'move_id': move_id,
                'journal_id': journal_id,
                'period_id': period_id,
                'date': entry_date,
                'document_date': entry_date,
                'account_id': random_account_id,
                'name': name,
                'currency_id': booking_ccy_id,
                'amount_currency': random_amount,
            }
            if with_ad:
                distrib_id = self.create_analytic_distribution(
                    account_id=random_account_id)
                vals.update({'analytic_distribution_id': distrib_id})
            aml_id = self.proxy.aml.create(vals)
            if not aml_id:
                tpl = 'account move line creation failed :: %s'
                raise FinanceFlowException(tpl % (vals, ))

            # create JI counterpart(no ad)
            domain = [
                ('is_analytic_addicted', '!=', True),
                ('type', '=', 'receivable'),
            ]
            counterpart_account_ids = self.proxy.acc.search(domain)
            random_counterpart_account_id = choice(counterpart_account_ids)
            vals.update({
                'account_id': random_counterpart_account_id,
                'amount_currency': -1 * random_amount,
                'name': name + ' cp',
                'analytic_distribution_id': False,
            })
            aml_id = self.proxy.aml.create(vals)
            if not aml_id:
                tpl = 'account move line counterpart creation failed :: %s'
                raise FinanceFlowException(tpl % (vals, ))
                
            index += 1

        # validate JE
        self.proxy.am.button_validate([move_id])
        
    def create_register_line(self, regbr_or_id, code_or_id, amount,
            generate_distribution=False,
            date=False, document_date=False,
            third_partner_id=False, third_employee_id=False,
            third_journal_id=False, do_hard_post=False):
        """
        create a register line in the given register
        :param regbr_or_id: parent register browsed object or id
        :type regbr_or_id: object/int/long
        :param code_or_id: account code to search or account_id
        :type code_or_id: str/int/long
        :param amount: > 0 amount IN, < 0 amount OUT
        :param generate_distribution: (optional) if set to True generate a 
            compatible AD and attach it to the register line
        :param datetime date: posting date
        :param datetime document_date: document date
        :param third_partner_id: partner id
        :param third_employee_id: emp id (operational advance)
        :param third_journal_id: journal id (internal transfer)
        :return: register line id and AD id
        :rtype: tuple (register_line_id/ad_id or False)
        """
        # register
        if not regbr_or_id:
            raise FinanceFlowException("register missing")
        if isinstance(regbr_or_id, (int, long)):
            register_br = self.proxy.reg.browse(regbr_or_id)
        else:
            register_br = regbr_or_id

        # general account
        if isinstance(code_or_id, (str, unicode)):
            # check account code
            code_ids = self.proxy.acc.search(
                ['|', ('name', 'ilike', code), ('code', 'ilike', code)])
            if not code_ids or len(code_ids) != 1:
                tpl = "error searching for this account code: %s. need %s codes"
                raise FinanceFlowException(tpl % (code,
                    len(code_ids) > 1 and 'less' or 'more', ))
            account_id = code_ids[0]
        else:
            account_id = code_or_id
        account_br = self.proxy.acc.browse(account_id)

        # check dates
        if not date:
            date_start = register_br.period_id.date_start or False
            date_stop = register_br.period_id.date_stop or False
            if not date_start or not date_stop:
                tpl = "no date found for the period %s"
                raise FinanceFlowException(tpl % (
                    register_br.period_id.name, ))
            random_date = self.proxy.random_date(
                datetime.strptime(str(date_start), '%Y-%m-%d'),
                datetime.strptime(str(date_stop), '%Y-%m-%d')
            )
            date = datetime.strftime(random_date, '%Y-%m-%d')
        if not document_date:
            document_date = date

        # vals
        vals = {
            'statement_id': register_br.id,
            'account_id': account_id,
            'document_date': document_date,
            'date': date,
            'amount': amount,
            'name': MASK['register_line'] % (date, ),
        }
        if third_partner_id:
            vals['partner_id'] = third_partner_id
        if third_employee_id:
            vals['employee_id'] = third_employee_id
        if third_journal_id:
            vals['transfer_journal_id'] = third_journal_id
        if register_br.journal_id.type == 'cheque':
            vals['cheque_number'] = MASK['cheque_number'] % (
                self.proxy.get_uuid(), )

        # created and AD link
        regl_id = self.proxy.regl.create(vals)
        if generate_distribution and account_br.is_analytic_addicted:
            distrib_id = self.create_analytic_distribution(
                account_id=account_id)
            self.proxy.regl.write([regl_id],
                {'analytic_distribution_id': distrib_id}, {})
        else:
            distrib_id = False
        if do_hard_post:
            self.proxy.regl.button_hard_posting([regl_id], {})
        return regl_id, distrib_id

    def register_import_invoice(self, invoice_id, reg_br=False):
        """
        :param invoice_id: invoice id
        :param reg_br: browsed register or False to pick one randomly
            of adhoc invoice currency
        """
        ai_br = self.proxy.inv.browse(invoice_id)

        # check if adhoc state: 'draft' or 'open'
        if not ai_br.state in ('draft', 'open', ):
            tpl = "register_import_invoice invoice %d '%s' not 'draft' or" \
                " 'open'"
            self.log(tpl % (invoice_id, ai_br.name or ''), 'yellow')
            return False

        # check if opened (else do it: as it was finance side validated)
        posting_date = self.proxy.date2orm(ai_br.date_invoice)
        if ai_br.state == 'draft':
            # - open it
            # - force doc date to posting date (as by default to current date)
            vals = {
                'document_date': posting_date,
            }
            if not ai_br.check_total:
                vals['check_total'] = ai_br.amount_total
            self.proxy.inv.write([invoice_id], vals)
            self.proxy.exec_workflow('account.invoice', 'invoice_open',
                invoice_id)
                
        period_id = self.get_period(posting_date)

        # invoice's register (from invoice posting date)
        if reg_br:
            reg_id = reg_br.id
            rtype = reg_br.journal_id.type
        else:
            # register not passed:
            # randomly pick and browse one of 3 cash/bank/cheque register
            # of the adhoc currency
            rtype = choice([ 'cash', 'bank', 'cheque', ])
            domain = [
                ('period_id', '=', period_id),
                ('journal_id.currency', '=', ai_br.currency_id.id),
                ('journal_id.type', '=', rtype),  # see register_accounting
                                                 # account_bank_statement.py
                                                 # get_statement() (server action)
            ]
            reg_ids = self.proxy.reg.search(domain)
            if not reg_ids:
                tpl = "no '%s' register found for period '%s' and currency '%s'"
                raise FinanceFlowException(tpl % (rtype, posting_date,
                    ai_br.currency_id.code))
            reg_id = reg_ids[0]
            reg_br = self.proxy.reg.browse(reg_id)

        # simulate register "pending payement" button (wizard.import.invoice)
        # + single import + ok

        # create import wizard
        # see:
        #   - register_accounting/account_bank_statement.py:
        #       button_wiz_import_invoices()
        #   - register_accounting/wizard/import_invoices_on_registers.py
        vals = {
            'statement_id': reg_id,
            'currency_id': reg_br.currency.id,
        }
        context = {
            'from_cheque': rtype == 'cheque' or False,
            'st_id': reg_id,
            'st_period_id': period_id,
        }
        wii_id = self.proxy.inv_imp.create(vals, context)

        # search the invoice line in 'importable' invoices list
        domain = [
            # tuples for importable invoices moves (as in wizard)...
            ('ready_for_import_in_register', '=', True),
            ('currency_id', '=', reg_br.currency.id),
            ('invoice_line_id', '=', False),
            # ...the move of the invoice we are in to simulate
            ('move_id', '=', ai_br.move_id.id),
        ]
        aml_ids = self.proxy.aml.search(domain)
        if aml_ids:  # so not already imported
            # single import
            self.proxy.inv_imp.write([wii_id],
                {'line_ids': [(6, 0, [aml_ids[0]])]}, context)
            self.proxy.inv_imp.single_import([wii_id], context)
            
            # post update wizard lines (dates in register period)
            wii_br = self.proxy.inv_imp.browse(wii_id)
            if wii_br and wii_br.invoice_lines_ids:
                line = self.proxy.get_iter_item(wii_br.invoice_lines_ids, 0)
                if line:
                    vals = {
                        'date': posting_date,
                        'document_date': posting_date,
                    }
                    if rtype == 'cheque':
                        vals['cheque_number'] = MASK['cheque_number'] % (
                            self.proxy.get_uuid(), )
                    self.proxy.inv_imp_line.write([line.id], vals, context)

            # confirm
            res = self.proxy.inv_imp.action_confirm([wii_id], context)

            # simulate imported invoice register line hard post
            if res and res.get('st_line_ids', False):       
                self.proxy.regl.button_hard_posting(res['st_line_ids'], context)

        return True


class FinanceSetup(FinanceFlowBase):
    def __init__(self, proxy):
        super(FinanceSetup, self).__init__(proxy)
        
    def _fy_create_with_periods(self, year):
        """
        create fy and periods (and special ones) for given fy by year
        :return fy id
        """
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        
        fiscalyear_id = self.proxy.fy.create({
            'name': 'FY %d' % (start_date.year),
            'code': 'FY%d' % (start_date.year),
            'date_start': start_date.strftime('%Y-%m-%d'),
            'date_stop': end_date.strftime('%Y-%m-%d'),
        })

        ds = start_date
        while ds < end_date:
            de = ds + relativedelta(months=1, days=-1)
            if de > end_date:
                de = end_date

            self.proxy.per.create({
                'name': ds.strftime('%b %Y'),
                'code': ds.strftime('%b %Y'),
                'date_start': ds.strftime('%Y-%m-%d'),
                'date_stop': de.strftime('%Y-%m-%d'),
                'fiscalyear_id': fiscalyear_id,
                'number': int(ds.strftime('%m')),
            })
            ds = ds + relativedelta(months=1)

        for period_nb in (13, 14, 15):
            self.proxy.per.create({
                'name': 'Period %d' % (period_nb),
                'code': 'Period %d' % (period_nb),
                'date_start': '%d-12-01' % (start_date.year),
                'date_stop': '%d-12-31' % (start_date.year),
                'fiscalyear_id': fiscalyear_id,
                'special': True,
                'number': period_nb,
            })
            
        return fiscalyear_id

    def check_fy(self, year):
        """
        open current FY
        """
        # search for current FY
        domain = [
            ('date_start', '=', self.get_date_for_month(1, year, day=1)),
            ('date_stop', '=', self.get_date_for_month(12, year, day=31)),
        ]
        fy_ids = self.proxy.fy.search(domain)
        if not fy_ids:
            fy_id = self._fy_create_with_periods(year)
            self.proxy.log("FY %d created" % (year, ), 'yellow')
        else:
            fy_id = fy_ids[0]

        # open periods (sorted by date)
        domain = [
            ('fiscalyear_id', '=', fy_id),
            ('special', '!=', True),  # skip 13-15 periods
            ('state', '=', 'created'),  # draft
        ]
        period_ids = self.proxy.per.search(domain, 0, None, 'date_start')
        if period_ids:
            # periods to open
            self.proxy.per.action_open_period(period_ids)
            ids_opened = ",".join(map(lambda x: str(x), period_ids))
            self.proxy.log("Periods opened: %s" % (ids_opened, ), 'yellow')
        
    def open_registers(self, start_year, year_count, ccy_ids):
        """
        create/open (cash, bank, cheque) for each period of FY
        :param ccy_code: currency
        """
        types = ('cash', 'bank', 'cheque', )
        account_codes_map = {
            'cash': '10100',
            'bank': '10200',
            'cheque': '10210',
        }

        start_date = "%d-01-01" % (start_year, )
        start_period_id = self.get_period(start_date)
        any_created = False

        for ccy_br in self.proxy.ccy.browse(ccy_ids):
            ccy_code = ccy_br.name

            # base registers (create and open if needed)
            bank_journal_id = False
            reg_ids = []
            for t in types:
                code = "%s %s" % (t, ccy_code, )
                code = code.upper()
                name = MASK['register'] % (t, ccy_code, )
                domain = [
                    ('type', '=', t),
                    ('currency', '=', ccy_br.id),
                    ('name', '=', name),
                ]
                aj_ids = self.proxy.journal.search(domain)
                if not aj_ids:
                    any_created = True
                    reg_id, journal_id = self.create_register(name, code, t,
                        account_codes_map[t], ccy_code,
                        bank_journal_id=bank_journal_id)
                    # force the period of the register
                    # by default in current period
                    self.proxy.reg.write([reg_id],
                        {'period_id': start_period_id})
                    if t == 'bank':
                        bank_journal_id = journal_id
                    if reg_id and journal_id:
                        reg_ids.append(reg_id)
                        self.proxy.log("base register %s created" % (code, ))

            # open start registers and create/open others
            if reg_ids:
                self.proxy.log('other fy registers creation')
                
                # open start registers...
                self.open_register(reg_ids)

                # ...then create new others registers (register creation wizard)
                i = 0
                while i < year_count:
                    year = start_year + i
                    start_month = 2 if i == 0 else 1
                    for m in xrange(start_month, 13):
                        curr_date = "%04d-%02d-01" % (year, m, )
                        period_id = self.get_period(curr_date)
                        instance_id = self.proxy.login.company_id.instance_id.id
                        fake_context = {'fake': 1}
                        vals = {
                            'period_id': period_id,
                            'instance_id': instance_id,
                        }
                        wrc_id = self.proxy.reg_cr.create(vals, fake_context)
                        self.proxy.reg_cr.button_confirm_period([wrc_id],
                            fake_context)
                        self.proxy.reg_cr.button_create_registers([wrc_id],
                            fake_context)

                        reg_ids = self.proxy.reg.search(
                            [('period_id', '=', period_id)])
                        if reg_ids:
                            # post change date...
                            for rid in reg_ids:
                                self.proxy.reg.write(rid, {'date': curr_date})
                            # ...and open them
                            self.open_register(reg_ids)
                    i += 1
        
        if any_created:            
            self.proxy.log('registers created', 'yellow')
                    
    def run(self):
        self.proxy.log("finance setup", 'yellow')
        
        # active all analytical child accounts since FY14 start
        # (bypass recursion check)
        self.proxy.log("finance setup - analytical accounts: active date_start")
        aaa_ids = self.proxy.ana_acc.search([('parent_id', '!=', False)])
        for aaa_br in self.proxy.ana_acc.browse(aaa_ids):
            self.proxy.ana_acc.write(aaa_br.id, {
                'parent_id': aaa_br.parent_id.id,
                'date_start': '2014-01-01',
            })
        
        # check FYs
        # - create fy with its periods if missing
        # - open draft periods
        start_year = self.get_cfg_int('fy_start')
        year_count = self.get_cfg_int('fy_count')
        year_index = 0
        while year_index < year_count:
            year = start_year + year_index
            self.proxy.log("finance setup - check FY %d" % (year, ))
            self.check_fy(year)
            
            year_index += 1
        
        # open registers for active currencies (from 2014)
        self.proxy.log("finance setup - check registers")
        self.open_registers(start_year, year_count, self.proxy.ccy.search(
            []))
        
class FinanceMassGen(FinanceFlowBase):
    """
    Mass data generation of finance data
    """
    def __init__(self, proxy):
        super(FinanceMassGen, self).__init__(proxy)

    def run(self, command):
        self.proxy.log("finance mass generation %s" % (command, ),
            color_code='yellow')
        if command == 'fin_je':
            self.direct_entries()
        
    def direct_entries(self):
        ccy_ids = self.proxy.ccy.search([])
        if not ccy_ids:
            return
        
        fy_start = self.get_cfg_int('fy_start')
        if TEST_MODE:
            fy_count = self.get_cfg_int('fy_count') \
                if TEST_MODE != 'unit' else 1
        else:
            fy_count = self.get_cfg_int('fy_count')
        
        je_per_month = 1 if TEST_MODE and TEST_MODE != 'full_1st_period' \
            else self.get_cfg_int('je_per_month')
        ji_min_count = self.get_cfg_int('ji_min_count')
        ji_max_count = self.get_cfg_int('ji_max_count')
        
        year_index = 0
        while year_index < fy_count:
            for m in xrange(1, 13):
                year = fy_start + year_index
                dt = "%04d-%02d-01" % (year, m, )
                self.proxy.log("%d JE for %s" % (je_per_month, dt, ))
                if TEST_MODE and TEST_MODE == 'fake':
                    continue
                
                for ccy_id in ccy_ids:
                    for je_index in xrange(0, je_per_month):
                        # random count of ji for each je of the period
                        ji_count = 2 if TEST_MODE and \
                            TEST_MODE != 'full_1st_period' \
                            else randrange(ji_min_count, ji_max_count)
                        self.chrono_start('ji', year, m)
                        self.create_journal_entry(ccy_id, year, m, ji_count,
                            True)
                        self.chrono_stop()
                        if TEST_MODE and TEST_MODE == 'unit':
                            return
                        
                # update report at each period process (in case of crash)
                self.chrono_report('finance_direct_entries', ('ji', ))
                if TEST_MODE == 'full_1st_period':
                    return
            year_index += 1
            

class FinanceFlow(FinanceFlowBase):
    """
    Flow to apply when supply has generated an invoice by reception
    """
    def __init__(self, proxy):
        super(FinanceFlow, self).__init__(proxy)
        
    def run(self):
        report_entry_types = (
            'regline_expense',
            'regline_not_expense',
            'regline_pending_payement',
            'regline_op_advance',
        )
        
        fy_start = self.get_cfg_int('fy_start')
        if TEST_MODE and TEST_MODE != 'full_1st_period':
            fy_count = self.get_cfg_int('fy_count') \
                if TEST_MODE != 'unit' else 1
            reg_expenses_max = 1
            reg_not_expenses_max = 1
            reg_pending_payement_max = 1
            reg_operational_advance_max = 1
        else:
            fy_count = self.get_cfg_int('fy_count')
            reg_expenses_max = self.get_cfg_int('reg_expenses_max')
            reg_not_expenses_max = self.get_cfg_int('reg_not_expenses_max')
            reg_pending_payement_max = self.get_cfg_int(
                'reg_pending_payement_max')
            reg_operational_advance_max = self.get_cfg_int(
                'reg_operational_advance_max')
        
        year_index = 0
        while year_index < fy_count:
            for m in xrange(1, 13):
                year = fy_start + year_index
                dt = "%04d-%02d-01" % (year, m, )
                period_id = self.get_period(dt)
                period_br = self.proxy.per.browse(period_id)
                
                self.proxy.log("finance flow of %s" % (dt, ))
                
                if TEST_MODE == 'fake':
                    continue
                
                # period's register
                reg_ids = self.proxy.reg.search([('period_id', '=', period_id)])
                for reg_br in self.proxy.reg.browse(reg_ids):
                    # expense line with AD
                    """for e in xrange(0, reg_expenses_max):
                        self.chrono_start('regline_expense', year, m)
                        self._create_random_expense_register_line(reg_br)
                        self.chrono_stop()"""
                    
                    # not expense line not AD
                    """for e in xrange(0, reg_not_expenses_max):
                        self.chrono_start('regline_not_expense', year, m)
                        self._create_random_not_expense_register_line(reg_br)
                        self.chrono_stop()"""
                    
                    # pending payement (invoice import)
                    domain = [  # get invoices ids of register period/ccy
                        ('state', 'in', ('draft', 'open')),
                        ('currency_id', '=', reg_br.currency.id),
                        ('date_invoice', '>=', 
                            self.proxy.date2orm(period_br.date_start)),
                        ('date_invoice', '<=',
                            self.proxy.date2orm(period_br.date_stop)),
                    ]
                    invoice_ids = self.proxy.inv.search(domain)
                    if invoice_ids and \
                        len(invoice_ids) > reg_pending_payement_max:
                        invoice_ids = invoice_ids[:reg_pending_payement_max]
                    for inv_id in invoice_ids:
                        self.chrono_start('regline_pending_payement', year, m)
                        self.register_import_invoice(inv_id, reg_br=reg_br)
                        self.chrono_stop()

                    # operational advance (only for CASH register)
                    if reg_br.journal_id.type == 'cash':
                        for e in xrange(0, reg_operational_advance_max):
                            self.chrono_start('regline_op_advance', year, m)
                            self._create_operational_advance_line(reg_br)
                            self.chrono_stop()
                            
                # update report at each period process (in case of crash)
                self.chrono_report('finance_flow', report_entry_types)
                
                if TEST_MODE and TEST_MODE in ('unit', 'full_1st_period'):
                    break  # 1st period only
            if TEST_MODE and TEST_MODE in ('unit', 'full_1st_period'):
                break  # 1st FY only
            year_index += 1
                    
    def _create_random_expense_register_line(self, reg_br):
        expense_account_count = self.get_cfg_int(
            'expenses_account_max')
            
        # random expense account
        account_ids = self.get_account_from_account_type('expense', 
            is_analytic_addicted=True)
        if account_ids and len(account_ids) > expense_account_count:
            account_ids = account_ids[:expense_account_count]
            
        # random date in register month
        entry_date = self.get_random_date_for_period(reg_br.period_id)
        
        # random third party: partner or emp or no
        partner_id = False
        emp_id = False
        tp_mode = choice(['p', 'e', '-', ])
        if tp_mode == 'p':
            partner_id = self.get_partner('external')
        elif tp_mode == 'e':
            emp_id = self.get_employee()
        
        self.create_register_line(reg_br.id,
            choice(account_ids),  # random expense account
            self.get_random_amount(),  # random amount
            generate_distribution=True,
            date=entry_date, document_date=entry_date,
            third_partner_id=partner_id, third_employee_id=emp_id,
            third_journal_id=False, do_hard_post=True)
            
    def _create_random_not_expense_register_line(self, reg_br):
        # random payable account
        account_ids = self.get_account_from_account_type('payables', 
            is_analytic_addicted=False)
            
        # random date in register month
        entry_date = self.get_random_date_for_period(reg_br.period_id)
        
        # random third party: partner or emp or no
        partner_id = False
        emp_id = False
        tp_mode = choice(['p', 'e', '-', ])
        if tp_mode == 'p':
            partner_id = self.get_partner('external')
        elif tp_mode == 'e':
            emp_id = self.get_employee()
        
        self.create_register_line(reg_br.id,
            choice(account_ids),  # random expense account
            self.get_random_amount(),  # random amount
            generate_distribution=False,
            date=entry_date, document_date=entry_date,
            third_partner_id=partner_id, third_employee_id=emp_id,
            third_journal_id=False, do_hard_post=True)
            
    def _create_operational_advance_line(self, reg_br):
        # random operational advance account
        domain = [
            ('type', '!=', 'view'),
            ('type_for_register', '=', 'advance'),
        ]
        account_ids = self.proxy.acc.search(domain)
        if not account_ids:
            raise FinanceFlowException('no operational advance account found')
            
        amount = self.get_random_amount()
            
        # random date in register month
        entry_date = self.get_random_date_for_period(reg_br.period_id)
        
        # third-party expat employee for the operational advance
        emp_id = self.get_employee()
        
        # create operational advance line and hard post it...
        register_line_id, ad_id = self.create_register_line(reg_br.id,
            choice(account_ids),  # random expense account
            amount, generate_distribution=True,
            date=entry_date, document_date=entry_date,
            third_employee_id=emp_id, do_hard_post=True)
        if register_line_id:
            # ... after hard post, simulate the advance return
            fake_context = {'fake': 1}
            wiz_ar_id = self.proxy.reg_adv_return.create({}, fake_context)
            if wiz_ar_id:
                # on an expense 6 account with AD
                account_id = choice(self.get_account_from_account_type(
                    'expense', is_analytic_addicted=True))
                ad_id = self.create_analytic_distribution(account_id=account_id)
                    
                # expense line (with full amount return)
                line_vals = {
                    'document_date': entry_date,
                    'description': "adv return %s" % (entry_date, ),
                    'account_id': account_id,
                    'partner_id': False,
                    'employee_id': emp_id,
                    'amount': amount,
                    'analytic_distribution_id': ad_id,
                }
                
                vals = {
                    'initial_amount': amount,
                    'returned_amount': 0,
                    'additional_amount': 0.,
                    'advance_st_line_id': register_line_id,
                    'advance_line_ids': [(0, 0, line_vals)],
                    'currency_id': reg_br.journal_id.currency.id,
                    'date':  entry_date,  # date of return,
                    'analytic_distribution_id': ad_id,
                }
                self.proxy.reg_adv_return.write([wiz_ar_id], vals)
                self.proxy.reg_adv_return.compute_total_amount([wiz_ar_id],
                    fake_context)
                # note checked delta in action_confirm_cash_return
                # wizard.initial_amount + wizard.additional_amount
                # - wizard.total_amount > 10**-3
                # wizard.total_amount <=> total of wizard lines amount
                self.proxy.reg_adv_return.action_confirm_cash_return(
                    [wiz_ar_id], fake_context)

# EOF
