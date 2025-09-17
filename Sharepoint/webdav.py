# -*- coding: utf-8 -*-

import requests
from office365.sharepoint.client_context import ClientContext
from office365.runtime.http.request_options import RequestOptions
from office365.runtime.http.http_method import HttpMethod
import uuid
import logging
import os
import posixpath
import time
from urllib.parse import urlparse, urljoin
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.primitives import hashes


class ConnectionFailed(Exception):
    pass

class PasswordFailed(Exception):
    pass

class Client(object):
    def __init__(self, host, tenant=None, client_id=None, cert_path=None, cert_content=None, protocol='https', path=None, *a, **b):
        self.requests_timeout = 45
        self.session_uuid = False
        self.session_offset = -1
        self.session_nb_error = 0

        self.tenant = tenant
        self.client_id = client_id
        self.cert_content = cert_content
        if self.cert_content is None:
            with open(cert_path, 'r') as c:
                self.cert_content = c.read()

        cert = load_pem_x509_certificate(bytes(self.cert_content, 'utf8'))
        self.thumbprint = cert.fingerprint(hashes.SHA1()).hex()


        self.path = path or ''

        self.url = '{0}://{1}'.format(protocol, host)

        self.login()

    def login(self):

        self.request = ClientContext(urljoin(self.url, self.path))

        ctx = self.request.with_client_certificate(
            tenant=self.tenant,
            client_id=self.client_id,
            private_key=self.cert_content,
            thumbprint=self.thumbprint,
        )
        baseurl = ctx._get_context_web_information().WebFullUrl
        ctx._auth_context.url = baseurl

        if not baseurl:
            raise requests.exceptions.RequestException("Full Url not found %s" % self.path)
        if not baseurl.endswith('/'):
            baseurl = '%s/' % baseurl
        parsed_base = urlparse(baseurl).path
        self.baseurl = '%s%s' % (self.url, parsed_base)

        if not self.path.startswith('/'):
            self.path = '/%s' % self.path
        if not self.path.endswith('/') and len(self.path) > 1:
            self.path = '%s/' % (self.path, )


    def format_request(self, url, method='POST', data="", session=False):
        assert(method in ['POST', 'DELETE'])
        r_meth = {
            'POST': HttpMethod.Post,
            'DELETE': HttpMethod.Delete,
        }
        options = RequestOptions(url)
        options.method = r_meth[method]
        options.set_header("X-HTTP-Method", method)
        options.set_header('Accept', 'application/json')
        options.set_header('Content-Type', 'application/json')
        self.request._authenticate_request(options)
        self.request._ensure_form_digest(options)

        if session:
            return session.post(url, data=data, headers=options.headers, auth=options.auth, timeout=self.requests_timeout)

        return requests.post(url, data=data, headers=options.headers, auth=options.auth, timeout=self.requests_timeout)

    def parse_error(self, result):
        try:
            if 'application/json' in result.headers.get('Content-Type'):
                resp_content = result.json()
                msg = resp_content['odata.error']['message']
                error = []
                if isinstance(msg, dict):
                    error = [msg['value']]
                else:
                    error = [msg]
                if resp_content['odata.error'].get('code'):
                    error.append('Code: %s' % resp_content['odata.error']['code'])
                return ' '.join(error)
        except:
            pass
        return result.content

    def create_folder(self, remote_path):
        webUri = '%s%s' % (self.path, remote_path)
        request_url = "%s_api/web/GetFolderByServerRelativeUrl('%s')" % (self.baseurl, webUri)
        result = self.format_request(request_url, 'POST')
        if result.status_code not in (200, 201):
            result = self.format_request("%s_api/Web/Folders/add('%s')" % (self.baseurl, webUri), 'POST')
            if result.status_code not in (200, 201):
                raise Exception(self.parse_error(result))
        return True

    def delete(self, remote_path):
        webUri = '%s%s' % (self.path, remote_path)
        request_url = "%s_api/web/getfilebyserverrelativeurl('%s')" % (self.baseurl, webUri)
        result = self.format_request(request_url, 'DELETE')
        if result.status_code not in (200, 201):
            raise Exception(self.parse_error(result))
        return True

    def move(self, remote_path, dest, retry=True):
        webUri = '%s%s' % (self.path, remote_path)
        destUri = '%s%s' % (self.path, dest)
        # falgs=1 to overwrite existing file
        request_url = "%s_api/web/getfilebyserverrelativeurl('%s')/moveto(newurl='%s',flags=1)" % (self.baseurl, webUri, destUri)
        result = self.format_request(request_url, 'POST')
        if result.status_code not in (200, 201):
            error = self.parse_error(result)
            if retry and ('timed out' in error or '2130575252' in error):
                logging.getLogger('cloud.backup').info('OneDrive move: session time out')
                self.login()
                return self.move(remote_path, dest, retry=False)
            raise Exception(self.parse_error(result))
        return True

    def upload(self, fileobj, remote_path, buffer_size=None, log=False, progress_obj=False, continuation=False):
        if not self.session_uuid:
            self.session_uuid = uuid.uuid1()

        if progress_obj:
            log = True

        if log:
            logger = logging.getLogger('cloud.backup')
            try:
                size = os.path.getsize(fileobj.name)
            except:
                size = None

        if not continuation:
            self.session_offset = -1

        if self.session_offset != -1:
            fileobj.seek(self.session_offset)

        if not buffer_size:
            buffer_size = 10* 1024 * 1024

        x = ""
        split_name = remote_path.split('/')
        new_file = split_name.pop()
        split_name.insert(0, self.path)
        path  = '/'.join(split_name)
        if path[-1] != '/':
            path += '/'
        webUri = '%s%s' % (path, new_file)
        s = requests.Session()

        while True:
            if self.session_offset == -1:
                # first loop create an empty file
                request_url = "%s_api/web/GetFolderByServerRelativeUrl('%s')/Files/add(url='%s',overwrite=true)" % (self.baseurl, path, new_file)
                self.session_offset = 0
            else:
                x = fileobj.read(buffer_size)
                if not x:
                    break
                if not self.session_offset:
                    # 2nd loop
                    if len(x) == buffer_size:
                        # split needed
                        request_url="%s_api/web/getfilebyserverrelativeurl('%s')/startupload(uploadId=guid'%s')" % (self.baseurl, webUri, self.session_uuid)
                    else:
                        # file size < buffer: no need to split
                        request_url = "%s_api/web/GetFolderByServerRelativeUrl('%s')/Files/add(url='%s',overwrite=true)" % (self.baseurl, path, new_file)
                elif len(x) == buffer_size:
                    request_url = "%s_api/web/getfilebyserverrelativeurl('%s')/continueupload(uploadId=guid'%s',fileOffset=%s)" % (self.baseurl, webUri, self.session_uuid, self.session_offset)
                else:
                    request_url = "%s_api/web/getfilebyserverrelativeurl('%s')/finishupload(uploadId=guid'%s',fileOffset=%s)" % (self.baseurl, webUri, self.session_uuid, self.session_offset)

            result = self.format_request(request_url, method='POST', data=x, session=s)
            if result.status_code not in (200, 201):
                return (False, self.parse_error(result))
            self.session_nb_error = 0
            self.session_offset += len(x)

            if log and self.session_offset and self.session_offset % (buffer_size*5) == 0:
                percent_txt = ''
                if size:
                    percent = round(self.session_offset*100/size)
                    percent_txt = '%d%%' % percent
                    if progress_obj:
                        progress_obj.write({'name': percent})

                logger.info('OneDrive: %d bytes sent on %s bytes %s' % (self.session_offset, size or 'unknown', percent_txt))
        self.session_offset = -1
        return (True, '')

    def list(self, remote_path):
        if not remote_path.startswith(self.path):
            remote_path = posixpath.join(self.path, remote_path)
        request_url = "%s_api/web/getfolderbyserverrelativeurl('%s')/files" % (self.baseurl, remote_path)
        options = RequestOptions(request_url)
        options.method = HttpMethod.Get
        options.set_header("X-HTTP-Method", "GET")
        options.set_header('accept', 'application/json;odata=verbose')
        self.request._authenticate_request(options)
        self.request._ensure_form_digest(options)
        result = requests.get(url=request_url, headers=options.headers)
        if result.status_code not in (200, 201):
            raise requests.exceptions.RequestException(self.parse_error(result))

        result = result.json()
        files=[]
        for i in range(len(result['d']['results'])):
            item = result['d']['results'][i]
            files.append(item)
        return files


    def download(self, remote_path, filename):
        if not remote_path.startswith(self.path):
            remote_path = posixpath.join(self.path, remote_path)
        request_url = "%s_api/web/getfilebyserverrelativeurl('%s')/$value" % (self.baseurl, remote_path)
        options = RequestOptions(request_url)
        options.method = HttpMethod.Get
        options.set_header("X-HTTP-Method", "GET")
        options.set_header('accept', 'application/json;odata=verbose')
        retry = 5
        while retry:
            try:
                self.request._authenticate_request(options)
                self.request._ensure_form_digest(options)
                with requests.get(url=request_url, headers=options.headers, auth=options.auth, stream=True, timeout=120) as r:
                    if r.status_code not in (200, 201):
                        error = self.parse_error(r)
                        raise requests.exceptions.RequestException(error)

                    with open(filename, 'wb') as file:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                file.write(chunk)
            except requests.exceptions.RequestException:
                time.sleep(3)
                self.login()
                retry -= 1
                if not retry:
                    raise
                continue

            retry = 0

        return filename

