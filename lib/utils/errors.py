# -*- coding: utf-8 -*-

__all__ = ['AuthenticationError', 'TinyException', 'TinyError',
           'TinyWarning', 'TinyMessage', 'Concurrency', 'AccessDenied']

class AuthenticationError(Exception): pass


class TinyException(Exception):

    def __init__(self, message, title=None):

        self.title = title
        self.message = message

    def __unicode__(self):
        return ustr(self.message)

    def __str__(self):
        return self.message

class TinyError(TinyException):

    def __init__(self, message, title=None):
        if title is None: title = "Error"
        TinyException.__init__(self, message=message, title=title)

class TinyWarning(TinyException):

    def __init__(self, message, title=None):
        if title is None: title = "Warning"
        TinyException.__init__(self, message=message, title=title)

class TinyMessage(TinyException):

    def __init__(self, message, title=None):
        if title is None: title = "Information"
        TinyException.__init__(self, message=message, title=title)

class Concurrency(Exception):

    def __init__(self, message, title=None, datas=None):
        self.title = title
        self.datas = datas
        self.message = message

    def __unicode__(self):
        return ustr(self.title)

    def __str__(self):
        return self.title

class AccessDenied(TinyError): pass

def error(title, msg):
    raise TinyError(message=msg, title=title or "Error")

def warning(msg, title=None):
    raise TinyWarning(message=msg, title=title or "Warning")

def message(msg):
    raise TinyMessage(message=msg)

def concurrency(msg, title=None, datas=None):
    raise Concurrency(message=msg, title=title, datas=datas)

