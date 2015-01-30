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
            aaj_ids = self.proxy.ajournal.search(
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
        aaj_ids = self.proxy.ajournal.search([('code', '=', aaj_code)])
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


class FinanceSetupFlow(FinanceFlowBase):
    def __init__(self, proxy):
        super(FinanceSetupFlow, self).__init__(proxy)

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
                    ('currency', '=', ccy_ids[0]),
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


class FinanceFlow(FinanceFlowBase):
    def __init__(self, proxy):
        super(FinanceFlow, self).__init__(proxy)

    def run(self, invoice_id):
        pass
