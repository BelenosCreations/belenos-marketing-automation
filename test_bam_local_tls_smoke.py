"""Full local HTTPS socket smoke test: BAM sign-in and first private draft.

Uses only ephemeral, loopback-only TLS and test data. Never contacts external
services or turns on social posting. Requires OpenSSL on the test runner.
"""
import json
import hashlib
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
    _QuietHandler,make_loopback_application,provision_preview_owner,
    add_preview_business)

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
            add_preview_business(str(dbfile),
                email='test-owner@example.com',
                password='a unique local test password',
                existing_tenant_id='example-shop',
                new_tenant_id='second-business',
                display_name='Second Service Business',
                industry='services',topic='facility care',now=101)
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
                    serve_browser_assets=True,
                    pending_media_dir=str(p/'private-media'))
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
                    def get(path,*,method='GET',body=None,token=None,
                            body_bytes=None,content_type=None,extra_headers=None):
                        headers={'Accept':'application/json'}
                        raw=None
                        if body is not None and body_bytes is not None:
                            raise ValueError('Choose JSON or raw bytes')
                        if body is not None:
                            raw=json.dumps(body).encode('utf-8')
                            headers['Content-Type']='application/json'
                        if body_bytes is not None:
                            raw=body_bytes
                            headers['Content-Type']=content_type
                        if extra_headers:
                            headers.update(extra_headers)
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
                        # A real loopback HTTPS byte transfer remains private.
                        from synthetic_media_fixture import PNG
                        png=PNG
                        digest=hashlib.sha256(png).hexdigest()
                        code,_,raw=get('/api/v1/content/upload-preflight',
                            method='POST',token=token,body={
                                'request_id':draft['request_id'],
                                'item':'image','media_type':'image/png',
                                'sha256':digest,'byte_count':len(png)})
                        self.assertEqual(code,202)
                        intent=json.loads(raw)
                        self.assertEqual(intent['status'],'pending')
                        self.assertIsNone(intent['upload_url'])
                        attachment=intent['attachment_id']
                        code,_,raw=get('/api/v1/content/media-status',
                            token=token)
                        self.assertEqual(code,200)
                        self.assertEqual(json.loads(raw)['items'],[{
                            'request_id':draft['request_id'],'item':'image',
                            'status':'awaiting_file'}])
                        code,_,raw=get('/api/v1/content/media-bytes',
                            method='PUT',token=token,body_bytes=png,
                            content_type='image/png',extra_headers={
                                'X-BAM-Attachment-ID':attachment})
                        self.assertEqual(code,202)
                        accepted=json.loads(raw)
                        self.assertEqual(accepted['status'],'pending_scan')
                        self.assertFalse(accepted['media_verified'])
                        self.assertFalse(accepted['publishing_enabled'])
                        self.assertEqual((p/'private-media'/(
                            attachment+'.pending')).read_bytes(),png)
                        code,_,raw=get('/api/v1/content/media-status',
                            token=token)
                        status=json.loads(raw)
                        self.assertEqual(status['items'][0]['status'],
                                         'pending_scan')
                        self.assertNotIn(attachment,str(status))
                        self.assertNotIn('storage_key',str(status))
                        code,_,raw=get('/api/v1/drafts',token=token)
                        self.assertEqual(json.loads(raw)['drafts'][0]['status'],
                                         'needs_content')
                        code,_,raw=get('/api/v1/content/media-pending',
                            method='DELETE',token=token,body={
                                'request_id':draft['request_id'],
                                'item':'image'})
                        self.assertEqual(code,200)
                        self.assertEqual(json.loads(raw)['removed'],1)
                        self.assertFalse((p/'private-media'/(
                            attachment+'.pending')).exists())
                        code,_,raw=get('/api/v1/content/media-status',
                            token=token)
                        self.assertEqual(json.loads(raw)['items'],[])
                        with self.assertRaises(urllib.error.HTTPError) as denied:
                            get('/README.md')
                        self.assertEqual(denied.exception.code,404)
                        with self.assertRaises(urllib.error.HTTPError) as denied:
                            get('/api/v1/publish',method='POST',body={})
                        self.assertEqual(denied.exception.code,404)
                        # Rotate sessions across owner-managed business tenants.
                        code,_,switched=get('/api/v1/businesses/activate',
                            method='POST',token=token,
                            body={'target_tenant_id':'second-business'})
                        self.assertEqual(code,200)
                        switched=json.loads(switched)
                        self.assertEqual(switched['tenant_id'],'second-business')
                        new_token=switched['session_token']
                        self.assertNotEqual(new_token,token)
                        with self.assertRaises(urllib.error.HTTPError) as old:
                            get('/api/v1/dashboard',token=token)
                        self.assertEqual(old.exception.code,401)
                        code,_,raw=get('/api/v1/dashboard',token=new_token)
                        self.assertEqual(json.loads(raw)['role'],'owner')
                        self.assertEqual(json.loads(raw)['tenant_id'],'second-business')
                        code,_,raw=get('/api/v1/drafts',token=new_token)
                        self.assertEqual(json.loads(raw)['drafts'],[])
                        code,_,raw=get('/api/v1/content/media-status',token=new_token)
                        self.assertEqual(json.loads(raw)['items'],[])
                        code,_,raw=get('/api/v1/auth/logout',method='POST',
                            token=new_token,body={})
                        self.assertTrue(json.loads(raw)['signed_out'])
                        with self.assertRaises(urllib.error.HTTPError) as denied:
                            get('/api/v1/dashboard',token=new_token)
                        self.assertEqual(denied.exception.code,401)
                    finally:
                        server.shutdown()
                        worker.join(timeout=5)
                        self.assertFalse(worker.is_alive())

if __name__=='__main__':
    unittest.main()
