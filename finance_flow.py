# -*- coding: utf-8 -*-
from random import randrange, choice, randint
from time import strftime
from datetime import datetime, timedelta

from chrono import TestChrono

class FinanceFlowBase(object):
    def __init__(self, proxy):
        self.proxy = proxy


class FinanceSetupFlow(FinanceFlowBase):
    def __init__(self, proxy):
        super(FinanceSetupFlow, self).__init__(proxy)

    def run(self):
        pass


class FinanceFlow(FinanceFlowBase):
    def __init__(self, proxy):
        super(FinanceFlow, self).__init__(proxy)

    def run(self, invoice_id):
        pass