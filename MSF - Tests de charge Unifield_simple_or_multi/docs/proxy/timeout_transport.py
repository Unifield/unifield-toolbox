import logging
import httplib
import xmlrpclib

class TimeoutHTTPConnection(httplib.HTTPConnection):

    def connect(self):
        httplib.HTTPConnection.connect(self)
        if self.timeout is not None:
            self.sock.settimeout(self.timeout)

class TimeoutHTTP(httplib.HTTP):

    _connection_class = TimeoutHTTPConnection

    def set_timeout(self, timeout):
        self._conn.timeout = timeout

class TimeoutTransport(xmlrpclib.Transport):

    def __init__(self, timeout=None, *args, **kwargs):
        xmlrpclib.Transport.__init__(self, *args, **kwargs)
        self.timeout = timeout

    def make_connection(self, host):
        self.realhost = host
        # TODO: check make_connection for python > 2.6
        conn = TimeoutHTTP('localhost:8080')
        conn.set_timeout(self.timeout)
        return conn
    def send_request(self, connection, handler, request_body):
        logger = logging.getLogger('TimeoutTransport')
        request = 'http://%s%s' % (self.realhost, handler)
        logger.info("request : %s", request)
        connection.putrequest('POST', request)
    def send_host(self, connection, host):
        connection.putheader('Host', self.realhost)

