# -*- coding: utf-8 -*-
from random import randrange, choice, randint
from time import strftime
from datetime import datetime, timedelta

from chrono import TestChrono


class FinanceFlowException(Exception):
    pass


class FinanceFlowBase(object):
    def __init__(self, proxy):
        self.proxy = proxy
        self.cache_clear()
        
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

    def get_partner(self, partner_type):
        """
        get first partner id from type
        :param partner_type: partner type
        :type partner_type: str
        :return:
        """
        partner_ids = self.proxy.partner.search(
            [('partner_type', '=', partner_type)])
        if not partner_ids:
            raise FinanceFlowException('partner not found')
        return partner_ids[0]

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
        domain = [('user_type', '=', acc_type_ids[0])]
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
                [('category', '=', 'DEST')])
            cost_center_id = company.instance_id.top_cost_center_id \
                and company.instance_id.top_cost_center_id.id or False
            funding_pool_id = funding_pool_pf_id
        else:
            # random DEST/FP from account via 'account.destination.link'
            # (PF randomly taken too) and compatible CC
            adl_ids = self.proxy.acc_dest_link.search(
                [('account_id', '=', account_id)])
            if adl_ids:
                adl_br = self.proxy.acc_dest_link.browse(choice(adl_ids))
                
                destination_ids = [adl_br.destination_id.id]
                
                # FP
                if adl_br.funding_pool_ids:
                    funding_pool_ids = [f.id for f in adl_br.funding_pool_ids]
                    funding_pool_ids.append(funding_pool_pf_id)
                else:
                    funding_pool_ids = [funding_pool_pf_id]
                funding_pool_id = choice(funding_pool_ids)
                
                # random CC compatible with FP
                if funding_pool_id == funding_pool_pf_id:
                    # PF FP so any CC valid
                    cost_center_ids = self.proxy.ana_acc.search(
                        [('category', '=', 'OC')])
                else:
                    fp_br = self.proxy.ana_acc.browse(funding_pool_id)
                    cost_center_ids = [ cc.id for cc in fp_br.cost_centers_ids]
                cost_center_id = choice(cost_center_ids)
            else:
                cost_center_id = instance.top_cost_center_id \
                    and instance.top_cost_center_id.id or False
                funding_pool_id = funding_pool_pf_id
                account = self.proxy.acc.browse(account_id)
                destination_ids = account.destination_ids
        if not destination_ids:
            raise FinanceFlowException('no destinations found')
        destination_id = choice(destination_ids)
            
        # create ad
        curr_date = self.current_date2orm()
        name = "auto AD %s" % (curr_date, )
        distrib_id = self.proxy.ad.create({'name': name})
        data = [
            ('cost.center.distribution.line', cost_center_id, False),
            ('funding.pool.distribution.line', funding_pool_id, cost_center_id),
        ]
        for analytic_obj, value, cc_id in data:
            vals = {
                'distribution_id': distrib_id,
                'name': "auto AD",
                'analytic_id': value,
                'cost_center_id': cc_id,
                'percentage': 100.0,
                'currency_id': company.currency_id.id,
                'destination_id': destination_id,
            }
            self.proxy.get(analytic_obj).create(vals)
        return distrib_id

    def create_journal_entry(self, month, with_ad):
        """
        create a JE (with 2 JI in it (expense and counterpart lines)
        :param with_ad: True if AD should be generated
        :type with_ad: boolean
        """
        month_str = "%02d" % (month, )
        rday = randint(1, 30)
        day = 28 if rday > 28 and month == 2 else rday
        day_str = "%02d" % (day, )
        curr_date = strftime('%Y-' + month_str + '-' + day_str)

        random_amount = randint(100, 10000)

        # purchase journal
        journal_id = self.get_purchase_journal()

        # current period
        period_id = self.get_period(curr_date)

        # partner (external)
        partner_id = self.get_partner('external')

        # create JE
        name = 'auto JE %s' % (curr_date, )
        entry_name = name
        vals = {
            'journal_id': journal_id,
            'period_id': period_id,
            'date': curr_date,
            'document_date': curr_date,
            'partner_id': partner_id,
            'status': 'manu',
            'name': name,
            'manual_name': name,
        }
        move_id = self.proxy.am.create(vals)
        if not id:
            raise FinanceFlowException('account move creation failed :: %s' % (
                vals, ))

        # create JI
        name = "auto JI %s" % (curr_date, )
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
            'date': curr_date,
            'document_date': curr_date,
            'account_id': random_account_id,
            'name': name,
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

        # create JI counterpart
        name = "auto JI %s counterpart" % (curr_date, )
        domain = [
            ('is_analytic_addicted', '!=', True),
            ('type', '=', 'receivable'),
        ]
        counterpart_account_ids = self.proxy.acc.search(domain)
        random_counterpart_account_id = choice(counterpart_account_ids)
        vals.update({
            'account_id': random_counterpart_account_id,
            'amount_currency': -1 * random_amount,
            'name': name,
            'analytic_distribution_id': False,
        })
        aml_id = self.proxy.aml.create(vals)
        if not aml_id:
            tpl = 'account move line counterpart creation failed :: %s'
            raise FinanceFlowException(tpl % (vals, ))

        # validate JE
        self.proxy.am.button_validate([move_id])
        
    def create_register_line(self, register_id, code_or_id, amount,
            generate_distribution=False,
            date=False, document_date=False,
            third_partner_id=False, third_employee_id=False,
            third_journal_id=False):
        """
        create a register line in the given register
        :param register_id: parent register id
        :param code_or_id: account code to search or account_id
        :type code_or_id: str/int/long
        :param amount: > 0 amount IN, < 0 amount OUT
        :param generate_distribution: (optional) if set to True generate a compatible AD and attach it to the register line
        :param datetime date: posting date
        :param datetime document_date: document date
        :param third_partner_id: partner id
        :param third_employee_id: emp id (operational advance)
        :param third_journal_id: journal id (internal transfer)
        :return: register line id and AD id
        :rtype: tuple (register_id/ad_id or False)
        """
        if not register_id:
            raise FinanceFlowException("register id missing")

        if is_instance(code_or_id, (str, unicode)):
            # check account code
            code_ids = self.proxy.acc.search(
                ['|', ('name', 'ilike', code), ('code', 'ilike', code)])
            if len(code_ids) != 1:
                tpl = "error searching for this account code: %s. need %s codes"
                raise FinanceFlowException(tpl % (code,
                    len(code_ids) > 1 and 'less' or 'more', ))
            account_id = code_ids[0]
        else:
            account_id = code_or_id

        register_br = self.proxy.reg.browse(register_id)
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
            'statement_id': register_id,
            'account_id': account_id,
            'document_date': document_date,
            'date': date,
            'amount': amount,
            'name': "auto %s" % (date, ),
        }
        if third_partner_id:
            vals['partner_id'] = third_partner_id
        if third_employee_id:
            vals['employee_id'] = third_employee_id
        if third_journal_id:
            vals['transfer_journal_id'] = third_journal_id

        # created and AD link
        regl_id = self.proxy.regl.create(vals)
        if generate_distribution and account_br.is_analytic_addicted:
            distrib_id = self.create_analytic_distribution(
                account_id=account_id)
            self.proxy.regl.write([regl_id],
                {'analytic_distribution_id': distrib_id})
        else:
            distrib_id = False
        return res, distrib_id

    def register_import_invoice(self, invoice_id):
        ai_br = self.proxy.inv.browse(invoice_id)

        # check if adhoc state: 'draft' or 'open'
        if not ai_br.state in ('draft', 'open', ):
            tpl = "register_import_invoice invoice %d '%s' not 'draft' or" \
                " 'open'"
            self.log(tpl % (invoice_id, ai_br.name or ''), 'yellow')
            return False

        # check if opened (else do it: as it was finance side validated)
        posting_date = self.date2orm(ai_br.date_invoice)
        if ai_br.state == 'draft':
            # open (bypass wizard.invoice_date check by setting missing values)
            vals = {}
            if not ai_br.document_date:
                vals['document_date'] = posting_date
            if not ai_br.check_total:
                vals['check_total'] = ai_br.amount_total
            if vals:
                self.proxy.inv.write([invoice_id], vals)
            self.proxy.exec_workflow('account.invoice', 'invoice_open',
                invoice_id)

        # invoice's register (from invoice posting date)
        # randomly pick and browse one of 3 cash/bank/cheque register
        period_id = self.get_period(posting_date)
        type = choice([ 'cash', 'bank', 'cheque', ])
        domain = [
            ('period_id', '=', period_id),
            ('journal_id.type', '=', type),  # see register_accounting
                                             # account_bank_statement.py
                                             # get_statement() (server action)
        ]
        reg_ids = self.proxy.reg.search(domain)
        if not reg_ids:
            tpl = "no '%s' register found for period '%s'"
            raise FinanceFlowException(tpl % (type, posting_date))
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
            'from_cheque': type == 'cheque' or False,
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
        if aml_ids:  # so not already
            # single import
            self.proxy.inv_imp.write([wii_id],
                {'line_ids': [(6, 0, [aml_ids[0]])]}, context)
            self.proxy.inv_imp.single_import([wii_id], context)

            # confirm
            if type == 'cheque':
                # provide cheque number before confirm
                wii_br = self.proxy.inv_imp.browse(wii_id)
                if wii_br and wii_br.invoice_lines_ids:
                    line = self.get_iter_item(wii_br.invoice_lines_ids, 0)
                    if line:
                        cheque_number = "CHK %s" % (ai_br.name or '', )
                        self.proxy.inv_impl.write([line.id],
                            {'cheque_number': cheque_number}, context)
            self.proxy.inv_imp.action_confirm([wii_id], context)
            self.log("import invoice '%s' in '%s' '%s' register" % (
                ai_br.name or '', type, posting_date, ))

            # simulate imported invoice register line hard post
            ai_br = self.proxy.inv.browse(invoice_id)
            # FIXME seem enough to identify unique imported confirmed line
            # FIXME but check if better can be done
            # identify imported confirmed line by:
            # statement/current date/ref<=>invoice origin/expense amount(< 0)
            domain = [
                ('statement_id', '=', reg_id),
                ('date', '=', self.current_date2orm()),
                ('ref', '=', ai_br.origin),
                ('amount', '=', ai_br.amount_total * -1),
            ]
            reg_line_ids = self.proxy.regl.search(domain)
            if reg_line_ids:
                #self.proxy.regl.button_temp_posting([reg_line_ids[0]], context)
                self.proxy.regl.button_hard_posting([reg_line_ids[0]], context)
            self.log("import invoice '%s' in '%s' '%s' register hard post" % (
                ai_br.name or '', type, posting_date, ))

        return True


class FinanceSetup(FinanceFlowBase):
    def __init__(self, proxy):
        super(FinanceSetup, self).__init__(proxy)

    def open_fy(self):
        """
        open current FY
        """
        curr_date = self.proxy.current_date2orm()

        # search for current FY
        domain = [
            ('date_start', '<=', curr_date),
            ('date_stop', '>=', curr_date),
        ]
        fy_ids = self.proxy.fy.search(domain)
        if not fy_ids:
            id = self.proxy.per_cr.create({'fiscalyear': 'current'})
            self.proxy.per_cr.account_period_create_periods([id])
            fy_ids = self.proxy.fy.search(domain)
            if not fy_ids:
                raise FinanceFlowException("Current FY creation failed")
            self.proxy.log('Current FY created', 'yellow')

        # check periods
        domain = [
            ('fiscalyear_id', '=', fy_ids[0]),
            ('special', '!=', True),  # skip 13-15 periods
            ('state', '=', 'created'),  # draft
        ]
        period_ids = self.proxy.per.search(domain)
        if period_ids:
            # periods to open (by chronological order)
            self.proxy.per.action_open_period(period_ids)
            ids_opened = ",".join(map(lambda x: str(x), period_ids))
            self.proxy.log("Periods opened: %s" % (ids_opened, ), 'yellow')
        
    def open_fy_registers(self, ccy_ids):
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

        for ccy_br in self.proxy.ccy.browse(ccy_ids):
            ccy_code = ccy_br.name

            # base (januar) registers (create and open if needed)
            bank_journal_id = False
            reg_ids = []
            for t in types:
                code = "%s %s" % (t, ccy_code, )
                code = code.upper()
                name = "auto %s %s" % (t, ccy_code, )
                domain = [
                    ('type', '=', t),
                    ('currency', '=', ccy_br.id),
                    ('name', '=', name),
                ]
                aj_ids = self.proxy.journal.search(domain)
                if not aj_ids:
                    reg_id, journal_id = self.create_register(name, code, t,
                        account_codes_map[t], ccy_code,
                        bank_journal_id=bank_journal_id)
                    if t == 'bank':
                        bank_journal_id = journal_id
                    if reg_id and journal_id:
                        reg_ids.append(reg_id)
                        self.proxy.log("register %s created" % (code, ))

            # open januar registers and create/open others

            if reg_ids:
                # open them (januar) registers...
                self.open_register(reg_ids)

                # ...then create new others registers (register creation wizard)
                for m in xrange(2, 13):
                    month_str = "%02d" % (m, )
                    curr_date = strftime('%Y-' + month_str + '-01')
                    period_id = self.get_period(curr_date)
                    wrc_id = self.proxy.reg_cr.create({'period_id': period_id})
                    self.proxy.reg_cr.button_confirm_period([wrc_id])
                    self.proxy.reg_cr.button_create_registers([wrc_id])

                    reg_ids = self.proxy.reg.search(
                        [('period_id', '=', period_id)])
                    if reg_ids:
                        # ...and open them
                        self.open_register(reg_ids)

    def run(self):
        # open current FY if needed
        self.open_fy()
        
        # open registers for active currencies
        self.open_fy_registers(self.proxy.ccy.search([]))
        

class FinanceMassGen(FinanceFlowBase):
    """
    Mass data generation of finance data
    """
    def __init__(self, proxy):
        super(FinanceMassGen, self).__init__(proxy)

    def run(self):
        self.proxy.log('finance mass generation', color_code='yellow')

class FinanceFlow(FinanceFlowBase):
    """
    Flow to apply when supply has generated an invoice by reception
    """
    def __init__(self, proxy):
        super(FinanceFlow, self).__init__(proxy)

    def run(self, invoice_id):
        pass
