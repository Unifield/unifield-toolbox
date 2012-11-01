import argparse

class ArgParse():
    def __init__(self, options=None):
        if options is None:
            options = []
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument("--dbname", "-d", metavar="dbname", default="unifield", help="database [default: %(default)s]")
        parser.add_argument("--host", "-H", metavar="host", default="127.0.0.1", help="Host [default: %(default)s]")
        parser.add_argument("--port", "-p", metavar="port", default="8069", help="Port [default: %(default)s]")
        parser.add_argument("--user", "-u", metavar="user", default="admin", help="User [default: %(default)s]")
        parser.add_argument("--password", "-w", metavar="pwd", default="admin", help="Password [default: %(default)s]")
        for opt1, opt2 in options:
            parser.add_argument(*opt1, **opt2)
        self.opt = parser.parse_args()

    def __getattr__(self, name):
        return getattr(self.opt, name)
