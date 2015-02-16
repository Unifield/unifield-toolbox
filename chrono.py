# -*- coding: utf-8 -*-

import time


class TestChrono(object):

    def __init__(self, name):
        self.name = name
        self.date_start = None
        self.start_time = None
        self.date_stop = None
        self.process_time = 0.00

    def __str__(self):
        if not self.date_start:
            return '%s :: Not started' % self.name
        elif self.date_start and not self.date_stop:
            return '%s :: Running' % self.name
        else:
            return '%s :: Start: %s :: End: %s :: Time: %s' % (
                self.name,
                self.date_start,
                self.date_stop,
                self.process_time
            )

    def start(self):
        self.date_start = time.strftime('%Y-%m-%d %H:%M:%S')
        self.start_time = time.time()

    def stop(self):
        self.process_time += time.time() - self.start_time
        self.date_stop = time.strftime('%Y-%m%d %H:%M:%S')

    def measure(self, f, *args, **kwargs):
        self.start()
        f(*args, **kwargs)
        self.stop()
