"""Full local HTTPS socket smoke test: BAM sign-in and first private draft.

Uses only ephemeral, loopback-only TLS and test data. Never contacts external
services or turns on social posting. Requires OpenSSL on the test runner.
"""
import json
from pathlib import Path
import shutil
import socket
import sqlite3
import ssl
import subprocess
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from wsgiref.simple_server import make_server

from bam_offline_gateway import BAMOfflineGateway
from bam_local_preview import (
    _QuietHandler,make_loopback_application,provision_preview_owner)

@unittest.skipUnless(shutil.which('openssl'),'OpenSSL unavailable')
class HTTPSPreviewSmokeTests(unittest.TestCase):
    def test_full_loopback_https_shell_password_and_held_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            dbfile=p/'preview.sqlite3'
            provision_preview_owner(str(dbfile),
                email='test-owner@example.com',
                password='a unique local test password',
                tenant_id='example-shop',display_name='Example Shop',
                industry='retail',topic='custom products',now=100)
            cert=p/'localhost-cert.pem'
            key=p/'localhost-key.pem'
            subprocess.run([
                shutil.which('openssl'),'req','-x509','-newkey','rsa:2048',
                '-nodes','-keyout',str(key),'-out',str(cert),
                '-days','1','-subj','/CN=localhost',
                '-addext','subjectAltName=DNS:localhost,IP:127.0.0.1'
            ],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            key.chmod(0o600)
            # Single-process WSGI and only one request at a time. In tests
            # the connection is opened from this test thread, served in worker.
            with sqlite3.connect(dbfile,check_same_thread=False) as db:
                gateway=BAMOfflineGateway(db,enabled=True,
                    serve_browser_assets=True)
                with make_server('127.0.0.1',0,
                    lambda environ,start:[],handler_class=_QuietHandler) as server:
                    port=server.server_port
                    server.set_app(make_loopback_application(gateway,port))
                    tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                    tls.minimum_version=ssl.TLSVersion.TLSv1_2
                    tls.load_cert_chain(str(cert),str(key))
                    server.socket=tls.wrap_socket(server.socket,server_side=True)
                    # No proxy; client verification disabled ONLY for ephemeral
                    # self-signed loopback test, never in a real BAM client.
                    test_tls=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                    test_tls.check_hostname=False
                    test_tls.verify_mode=ssl.CERT_NONE
                    opener=urllib.request.build_opener(
                        urllib.request.ProxyHandler({}),
                        urllib.request.HTTPSHandler(context=test_tls))
                    base='https://localhost:'+str(port)
                    def get(path,*,method='GET',body=None,token=None):
                        headers={'Accept':'application/json'}
                        raw=None
                        if body is not None:
                            raw=json.dumps(body).encode('utf-8')
                            headers['Content-Type']='application/json'
                        if token:
                            headers['Authorization']='Bearer '+token
                        request=urllib.request.Request(base+path,data=raw,
                            headers=headers,method=method)
                        with opener.open(request,timeout=8) as result:
                            return result.status,dict(result.headers),result.read()
                    worker=threading.Thread(target=server.serve_forever,daemon=True)
                    worker.start()
                    try:
                        code,headers,html=get('/')
                        self.assertEqual(code,200)
                        self.assertIn(b'Belenos Automatic Marketing',html)
                        self.assertIn(b'Content Studio',html)
                        self.assertIn("script-src 'self'",
                                      headers['Content-Security-Policy'])
                        code,_,js=get('/ui/bam_signed_in_shell.js')
                        self.assertEqual(code,200)
                        self.assertIn(b'BAMSignedInShell',js)
                        code,_,logo=get('/branding/source/app_icon.svg')
                        self.assertEqual(code,200)
                        self.assertIn(b'<svg',logo)
                        code,_,raw=get('/api/v1/auth/password',
                            method='POST',body={
                                'email':'test-owner@example.com',
                                'password':'a unique local test password',
                                'tenant_id':'example-shop'})
                        self.assertEqual(code,200)
                        token=json.loads(raw)['session_token']
                        self.assertGreater(len(token),32)
                        code,_,raw=get('/api/v1/dashboard',token=token)
                        dashboard=json.loads(raw)
                        self.assertEqual(dashboard['tenant_id'],'example-shop')
                        self.assertEqual(dashboard['role'],'owner')
                        self.assertFalse(dashboard['publishing_enabled'])
                        code,_,raw=get('/api/v1/content/drafts',method='POST',
                            token=token,body={
                                'channel':'facebook',
                                'draft_text':'Test product',
                                'suggestion':'Photograph approved sample',
                                'required_items':['image']})
                        self.assertEqual(code,201)
                        draft=json.loads(raw)
                        self.assertEqual(draft['status'],'needs_content')
                        self.assertFalse(draft['publishing_enabled'])
                        code,_,raw=get('/api/v1/drafts',token=token)
                        self.assertEqual(len(json.loads(raw)['drafts']),1)
                        with self.assertRaises(urllib.error.HTTPError) as denied:
                            get('/README.md')
                        self.assertEqual(denied.exception.code,404)
                        with self.assertRaises(urllib.error.HTTPError) as denied:
                            get('/api/v1/publish',method='POST',body={})
                        self.assertEqual(denied.exception.code,404)
                        code,_,raw=get('/api/v1/auth/logout',method='POST',
                            token=token,body={})
                        self.assertTrue(json.loads(raw)['signed_out'])
                        with self.assertRaises(urllib.error.HTTPError) as denied:
                            get('/api/v1/dashboard',token=token)
                        self.assertEqual(denied.exception.code,401)
                    finally:
                        server.shutdown()
                        worker.join(timeout=5)
                        self.assertFalse(worker.is_alive())

if __name__=='__main__':
    unittest.main()
