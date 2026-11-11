"""Local TLS preview has no public listener, secrets or trusted proxy shortcut."""
import io
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from bam_local_preview import (
    add_preview_business,make_loopback_application,provision_preview_owner,
    run_loopback_preview,_path)
from bam_offline_gateway import BAMOfflineGateway

class LoopbackTests(unittest.TestCase):
    def test_rejects_remote_and_dns_rebinding(self):
        observed=[]
        def gateway(environ,start):
            observed.append(environ)
            start('200 OK',[])
            return [b'allowed']
        app=make_loopback_application(gateway,8443)
        def call(address='127.0.0.1',host='localhost:8443',scheme='http'):
            got={}
            data=b''.join(app({'REMOTE_ADDR':address,'HTTP_HOST':host,
                'wsgi.url_scheme':scheme,
                'HTTP_X_FORWARDED_PROTO':'https'},
                lambda status,headers:got.update(status=status)))
            return got['status'],data
        self.assertEqual(call(),('200 OK',b'allowed'))
        self.assertEqual(observed[0]['wsgi.url_scheme'],'https')
        self.assertEqual(call(host='evil.example:8443')[0],'403 Forbidden')
        self.assertEqual(call(address='8.8.8.8')[0],'403 Forbidden')
        self.assertEqual(call(host='localhost:8080')[0],'403 Forbidden')
        self.assertEqual(len(observed),1)

    def test_no_insecure_or_unacknowledged_listener(self):
        with self.assertRaises(PermissionError):
            run_loopback_preview('/tmp/missing-preview.sqlite3',
                cert_path='/tmp/cert',key_path='/tmp/key')
        with self.assertRaises(ValueError):
            make_loopback_application(lambda env,start:[],80)
        with self.assertRaises(ValueError):
            run_loopback_preview('/tmp/missing-preview.sqlite3',
                cert_path='/tmp/cert',key_path='/tmp/key',
                port=80,explicit_opt_in=True)
        with self.assertRaises(ValueError):
            _path(str(Path(__file__).resolve().parent/'temp-preview.sqlite3'))
        self.assertTrue(_path('/tmp/example-preview.sqlite3').is_absolute())

class BootstrapTests(unittest.TestCase):
    def test_local_test_owner_can_sign_in_without_public_signup(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=str(Path(tmp)/'bam-preview.sqlite3')
            result=provision_preview_owner(file,
                email='operator@example.com',password='a strong test password',
                tenant_id='shop',display_name='Example Shop',
                industry='retail',topic='custom products',now=100)
            self.assertTrue(result['preview_only'])
            self.assertFalse(result['publishing_enabled'])
            with sqlite3.connect(file) as db:
                gateway=BAMOfflineGateway(db,enabled=True,
                    serve_browser_assets=True,clock=lambda:101)
                token=gateway.identities.login_password(
                    email='operator@example.com',
                    password='a strong test password',tenant_id='shop',now=101)
                view=gateway.read_api.get_dashboard_view(
                    session_token=token,server_now=101)
                self.assertEqual(view['tenant_id'],'shop')
                self.assertEqual(view['role'],'owner')
                self.assertFalse(view['publishing_enabled'])
            with self.assertRaises(PermissionError):
                provision_preview_owner(file,email='new@example.com',
                    password='a strong test password',tenant_id='other',
                    display_name='Other',industry='services',
                    topic='cleaning',now=102)
            if os.name=='posix':
                self.assertEqual(Path(file).stat().st_mode&0o077,0)

    def test_second_business_requires_existing_password_and_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=str(Path(tmp)/'multi-preview.sqlite3')
            provision_preview_owner(path,email='operator@example.com',
                password='a strong test password',tenant_id='first',
                display_name='First Shop',industry='retail',
                topic='products',now=100)
            with self.assertRaises(PermissionError):
                add_preview_business(path,email='operator@example.com',
                    password='incorrect password',existing_tenant_id='first',
                    new_tenant_id='second',display_name='Second Services',
                    industry='services',topic='cleaning',now=102)
            second=add_preview_business(path,email='operator@example.com',
                password='a strong test password',existing_tenant_id='first',
                new_tenant_id='second',display_name='Second Services',
                industry='services',topic='cleaning',now=103)
            self.assertEqual(second['business_id'],'second')
            self.assertFalse(second['publishing_enabled'])
            with sqlite3.connect(path) as db:
                gateway=BAMOfflineGateway(db,enabled=True,clock=lambda:105)
                token=gateway.identities.login_password(
                    email='operator@example.com',
                    password='a strong test password',
                    tenant_id='first',now=104)
                tenants=gateway.dashboard.switcher.list_businesses(
                    token=token,now=105)
                self.assertEqual({t['tenant_id'] for t in tenants},
                                 {'first','second'})
                switched=gateway.read_api.activate_business(
                    session_token=token,target_tenant_id='second',
                    server_now=105)
                self.assertEqual(switched['overview']['tenant_id'],'second')
                self.assertEqual(switched['overview']['role'],'owner')
                self.assertFalse(switched['publishing_enabled'])
                # The trusted HTTP adapter revokes the source session after
                # successful rotation; the lower-level service does not.
                self.assertIsNotNone(gateway.sessions.resolve(token,now=106))
                gateway.read_api.logout(session_token=token,server_now=106)
            with self.assertRaises(PermissionError):
                add_preview_business(path,email='operator@example.com',
                    password='a strong test password',existing_tenant_id='first',
                    new_tenant_id='second',display_name='Already Exists',
                    industry='services',topic='cleaning',now=107)

    def test_invalid_setup_does_not_create_user(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=str(Path(tmp)/'bad.sqlite3')
            for patch in ({'password':'weak'},
                          {'display_name':''},{'topic':''},
                          {'tenant_id':'x'*129},{'email':'bad-email'}):
                args=dict(email='operator@example.com',
                    password='a strong test password',tenant_id='shop',
                    display_name='Example Shop',industry='retail',
                    topic='custom products',now=100)
                args.update(patch)
                with self.assertRaises(ValueError):
                    provision_preview_owner(file,**args)
            self.assertFalse(Path(file).exists())

if __name__=='__main__':
    unittest.main()
