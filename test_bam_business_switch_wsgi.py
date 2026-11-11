"""Fail-closed security boundary tests for tenant session rotation."""
import io
import json
import unittest

from bam_business_switch_wsgi import BAMBusinessSwitchWSGI


class FakeSwitchAPI:
    def __init__(self):
        self.calls=[]
        self.fail_revoke=False
        self.fail_activate=False

    def activate_business(self, **kwargs):
        self.calls.append(('activate', kwargs))
        if self.fail_activate:
            raise PermissionError('Forbidden business')
        return {'session_token':'b'*43,
                'overview':{'tenant_id':'other'},
                'publishing_enabled':False}

    def logout(self, **kwargs):
        self.calls.append(('logout',kwargs))
        if self.fail_revoke and kwargs['session_token']=='a'*43:
            raise RuntimeError('Source revocation unavailable')
        return {'signed_out':True,'publishing_enabled':False}


class BAMBusinessSwitchWSGITests(unittest.TestCase):
    def setUp(self):
        self.api=FakeSwitchAPI()
        self.app=BAMBusinessSwitchWSGI(
            self.api,enabled=True,clock=lambda:100)

    def call(self,*,app=None,raw=None,body=None,**overrides):
        if raw is None:
            raw=json.dumps({'target_tenant_id':'other'} if body is None
                           else body).encode('utf-8')
        environ={'wsgi.url_scheme':'https',
                 'PATH_INFO':'/api/v1/businesses/activate',
                 'REQUEST_METHOD':'POST',
                 'HTTP_AUTHORIZATION':'Bearer '+'a'*43,
                 'CONTENT_TYPE':'application/json',
                 'CONTENT_LENGTH':str(len(raw)),
                 'wsgi.input':io.BytesIO(raw)}
        environ.update(overrides)
        got={}
        encoded=b''.join((app or self.app)(environ,
            lambda status,headers:got.update(status=status,
                headers=dict(headers))))
        return got,json.loads(encoded)

    def test_success_rotates_old_session_without_exposing_overview(self):
        meta,body=self.call()
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(body,{
            'tenant_id':'other','session_token':'b'*43,
            'publishing_enabled':False})
        self.assertEqual([x[0] for x in self.api.calls],
                         ['activate','logout'])
        self.assertEqual(self.api.calls[0][1]['session_token'],'a'*43)
        self.assertEqual(self.api.calls[0][1]['target_tenant_id'],'other')
        self.assertEqual(self.api.calls[1][1]['session_token'],'a'*43)
        self.assertEqual(meta['headers']['Cache-Control'],'no-store, private')

    def test_disabled_by_default(self):
        app=BAMBusinessSwitchWSGI(self.api)
        meta,result=self.call(app=app)
        self.assertEqual(meta['status'],'503 Service Unavailable')
        self.assertNotIn('session_token',result)
        self.assertEqual(self.api.calls,[])

    def test_membership_denial_preserves_source_session(self):
        self.api.fail_activate=True
        meta,body=self.call()
        self.assertEqual(meta['status'],'401 Unauthorized')
        self.assertNotIn('session_token',body)
        self.assertEqual(len(self.api.calls),1)

    def test_source_revocation_failure_rejects_new_session(self):
        self.api.fail_revoke=True
        meta,body=self.call()
        self.assertEqual(meta['status'],'503 Service Unavailable')
        self.assertNotIn('session_token',body)
        self.assertEqual([c[0] for c in self.api.calls],
                         ['activate','logout','logout'])
        self.assertEqual(self.api.calls[-1][1]['session_token'],'b'*43)

    def test_rejects_duplicate_fields_and_unexpected_privileges(self):
        for raw in (
            b'{"target_tenant_id":"other","target_tenant_id":"shop"}',
            b'{"target_tenant_id":"other","role":"owner"}',
            b'{"target_tenant_id":true}',
            b'{"target_tenant_id":" other "}',
            b'[]',b'{'):
            with self.subTest(raw=raw):
                meta,_=self.call(raw=raw)
                self.assertEqual(meta['status'],'400 Bad Request')
        self.assertEqual(self.api.calls,[])

    def test_deny_insecure_transport_and_invalid_bearer(self):
        meta,_=self.call(**{'wsgi.url_scheme':'http',
                            'HTTP_X_FORWARDED_PROTO':'https'})
        self.assertEqual(meta['status'],'403 Forbidden')
        for token in ('','Bearer invalid','Bearer '+'a'*43+' '):
            meta,_=self.call(HTTP_AUTHORIZATION=token)
            self.assertEqual(meta['status'],'401 Unauthorized')
        self.assertEqual(self.api.calls,[])

    def test_rejects_wrong_verb_path_and_size(self):
        for patch,expected in [
                ({'REQUEST_METHOD':'GET'},'405 Method Not Allowed'),
                ({'PATH_INFO':'/api/v1/publish'},'404 Not Found'),
                ({'CONTENT_LENGTH':'50000'},'400 Bad Request'),
                ({'CONTENT_TYPE':'text/plain'},'400 Bad Request')]:
            with self.subTest(patch=patch):
                meta,_=self.call(**patch)
                self.assertEqual(meta['status'],expected)
        self.assertEqual(self.api.calls,[])


if __name__=='__main__':
    unittest.main()
