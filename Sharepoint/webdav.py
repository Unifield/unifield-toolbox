# -*- coding: utf-8 -*-

import requests
from office365.sharepoint.client_context import ClientContext
from office365.runtime.client_request_exception import ClientRequestException
import posixpath
from urllib.parse import urlparse, urljoin
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.primitives import hashes


class ConnectionFailed(Exception):
    pass

class PasswordFailed(Exception):
    pass

class Client(object):
    def __init__(self, host, tenant=None, client_id=None, cert_path=None, cert_content=None, protocol='https', path=None, *a, **b):
        self.tenant = tenant
        self.client_id = client_id
        self.cert_content = cert_content
        if self.cert_content is None:
            with open(cert_path, 'r') as c:
                self.cert_content = c.read()
        cert = load_pem_x509_certificate(bytes(self.cert_content, 'utf8'))
        self.thumbprint = cert.fingerprint(hashes.SHA1()).hex()

        self.ctx = None

        self.path = path or ''

        self.url = '{0}://{1}'.format(protocol, host)

        self.login()

    def login(self):

        self.request = ClientContext(urljoin(self.url, self.path))

        self.request.with_client_certificate(
            tenant=self.tenant,
            client_id=self.client_id,
            private_key=self.cert_content,
            thumbprint=self.thumbprint,
        )
        baseurl = self.request._get_context_web_information().WebFullUrl
        self.request._auth_context.url = baseurl

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


    def create_folder(self, remote_path):
        webUri = '%s%s' % (self.path, remote_path)
        try:
            self.request.web.get_folder_by_server_relative_url(webUri).get().execute_query()
        except ClientRequestException as e:
            if e.response.status_code == 404:
                self.request.web.get_folder_by_server_relative_url(self.path).add(remote_path).execute_query()
            else:
                raise ValueError(e.response.text)

        return True

    def delete(self, remote_path):
        webUri = '%s%s' % (self.path, remote_path)
        return self.request.web.get_file_by_server_relative_url(webUri).delete_object().execute_query()

    def move(self, remote_path, dest, retry=True):
        webUri = '%s%s' % (self.path, remote_path)

        to_folder_dest = self.request.web.get_folder_by_server_relative_path(dest)
        return self.request.web.get_file_by_server_relative_path(webUri).moveto(to_folder_dest, 1).execute_query()

    def upload(self, fileobj, remote_path, buffer_size=None, log=False, progress_obj=False, continuation=False):

        split_name = remote_path.split('/')
        split_name.insert(0, self.path)
        path  = '/'.join(split_name)
        if path[-1] != '/':
            path += '/'

        if buffer_size is None:
            buffer_size = 10 * 1024 * 1024

        target_folder = self.request.web.get_folder_by_server_relative_url(path)
        target_folder.files.create_upload_session(
            fileobj, buffer_size
        ).execute_query()
        return True

    def list(self, remote_path):
        if not remote_path.startswith(self.path):
            remote_path = posixpath.join(self.path, remote_path)
        return (
            self.request.web.get_folder_by_server_relative_path(remote_path)
            .get_files()
            .expand(["TimeLastModified"])
            .execute_query()
        )

    def download(self, remote_path, filename):
        if not remote_path.startswith(self.path):
            remote_path = posixpath.join(self.path, remote_path)

        src = self.request.web.get_file_by_server_relative_path(remote_path)
        with open(filename, 'wb') as file:
            src.download_session(file).execute_query()
        return filename

