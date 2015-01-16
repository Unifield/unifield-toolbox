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

    def print_log(self, msg, color):
        self.proxy.log(msg, color)
        """if color:
            msg = color_str(msg, color)"""
        print msg

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
            self.print_log('Current FY created', 'yellow')

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
            self.print_log("Periods opened: %s" % (ids_opened, ), 'yellow')

    def run(self):
        self.open_fy()


class FinanceFlow(FinanceFlowBase):
    def __init__(self, proxy):
        super(FinanceFlow, self).__init__(proxy)

    def run(self, invoice_id):
        pass