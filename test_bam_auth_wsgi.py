"""Security regression tests for the disabled-by-default BAM login transport."""
import io
import json
import sqlite3
import unittest

from bam_auth_wsgi import BAMAuthWSGI


class FakeAuthAPI:
    throttle = object()

    def __init__(self):
        self.calls = []
        self.denied = False

    def password_login(self, **kwargs):
        self.calls.append(('password', kwargs))
        if self.denied:
            raise PermissionError('Sensitive account-specific reason')
        return {'session_token': 'a' * 43, 'publishing_enabled': False}

    def begin_google(self, **kwargs):
        self.calls.append(('begin', kwargs))
        return {'challenge_id': 'b' * 43, 'nonce': 'c' * 43,
                'expires_at': kwargs['server_now'] + 300}

    def google_login(self, **kwargs):
        self.calls.append(('google', kwargs))
        if self.denied:
            raise PermissionError('User not linked')
        return {'session_token': 'd' * 43, 'publishing_enabled': False}


class BAMAuthWSGITests(unittest.TestCase):
    def setUp(self):
        self.api = FakeAuthAPI()
        self.app = BAMAuthWSGI(self.api, enabled=True, clock=lambda: 100)

    def call(self, *, app=None, path='/api/v1/auth/password', body=None,
             raw=None, **environ_overrides):
        if raw is None:
            if body is None:
                body = {'email': 'owner@example.com',
                        'password': 'correct horse battery staple',
                        'tenant_id': 'shop'}
            raw = json.dumps(body).encode('utf-8')
        env = {'wsgi.url_scheme': 'https',
               'PATH_INFO': path, 'REQUEST_METHOD': 'POST',
               'CONTENT_TYPE': 'application/json',
               'CONTENT_LENGTH': str(len(raw)), 'wsgi.input': io.BytesIO(raw)}
        env.update(environ_overrides)
        metadata = {}
        data = b''.join((app or self.app)(
            env, lambda status, headers:
            metadata.update(status=status, headers=dict(headers))))
        return metadata, json.loads(data.decode('utf-8'))

    def test_disabled_by_default(self):
        app = BAMAuthWSGI(self.api)
        meta, payload = self.call(app=app)
        self.assertEqual(meta['status'], '503 Service Unavailable')
        self.assertNotIn('session_token', payload)
        self.assertEqual(self.api.calls, [])

    def test_enabled_requires_auth_throttle(self):
        api = FakeAuthAPI()
        api.throttle = None
        with self.assertRaises(ValueError):
            BAMAuthWSGI(api, enabled=True)

    def test_password_returns_only_unpublished_session(self):
        meta, body = self.call()
        self.assertEqual(meta['status'], '200 OK')
        self.assertEqual(body, {
            'session_token': 'a' * 43, 'publishing_enabled': False})
        self.assertEqual(meta['headers']['Cache-Control'], 'no-store, private')
        self.assertNotIn('Access-Control-Allow-Origin', meta['headers'])
        self.assertNotIn('correct horse', str(body))
        self.assertEqual(self.api.calls, [('password', {
            'email': 'owner@example.com',
            'password': 'correct horse battery staple',
            'tenant_id': 'shop', 'server_now': 100})])

    def test_malformed_and_extra_fields_denied(self):
        for body in [
            {'email': 'owner@example.com',
             'password': 'correct horse battery staple'},
            {'email': 'owner@example.com',
             'password': 'correct horse battery staple',
             'tenant_id': 'shop', 'role': 'owner'},
            {'email': 'owner@example.com',
             'password': 'correct horse battery staple',
             'tenant_id': 'shop', 'publishing_enabled': True},
            {'email': '', 'password': 'x', 'tenant_id': 'shop'},
            {'email': 'owner@example.com', 'password': [],
             'tenant_id': 'shop'}]:
            with self.subTest(body=body):
                meta, _ = self.call(body=body)
                self.assertEqual(meta['status'], '400 Bad Request')
        self.assertEqual(self.api.calls, [])

    def test_duplicate_keys_and_invalid_json_denied(self):
        duplicate = (
            b'{"email":"owner@example.com","email":"bad@example.com",'
            b'"password":"correct horse battery staple","tenant_id":"shop"}')
        for raw in (duplicate, b'{', b'[]', b'null'):
            with self.subTest(raw=raw):
                meta, _ = self.call(raw=raw)
                self.assertEqual(meta['status'], '400 Bad Request')
        self.assertEqual(self.api.calls, [])

    def test_https_required_and_client_proxy_claim_ignored(self):
        meta, _ = self.call(**{'wsgi.url_scheme': 'http',
                             'HTTP_X_FORWARDED_PROTO': 'https'})
        self.assertEqual(meta['status'], '403 Forbidden')
        self.assertEqual(self.api.calls, [])

    def test_only_expected_paths_and_method(self):
        meta, _ = self.call(path='/api/v1/auth/publish')
        self.assertEqual(meta['status'], '404 Not Found')
        meta, _ = self.call(REQUEST_METHOD='GET')
        self.assertEqual(meta['status'], '405 Method Not Allowed')
        self.assertEqual(self.api.calls, [])

    def test_size_and_media_type_bounds(self):
        for override in [{'CONTENT_LENGTH': '99999999'},
                         {'CONTENT_LENGTH': '-1'},
                         {'CONTENT_LENGTH': ''},
                         {'CONTENT_TYPE': 'text/plain'}]:
            with self.subTest(override=override):
                meta, _ = self.call(**override)
                self.assertEqual(meta['status'], '400 Bad Request')
        self.assertEqual(self.api.calls, [])

    def test_account_failures_are_generic(self):
        self.api.denied = True
        meta, body = self.call()
        self.assertEqual(meta['status'], '401 Unauthorized')
        self.assertEqual(body, {'error': 'Sign-in unavailable'})
        self.assertNotIn('Sensitive', str(body))

    def test_google_challenge_and_verified_login(self):
        meta, challenge = self.call(path='/api/v1/auth/google-challenge',
                                    body={})
        self.assertEqual(meta['status'], '200 OK')
        self.assertEqual(challenge['challenge_id'], 'b' * 43)
        self.assertEqual(challenge['nonce'], 'c' * 43)
        self.assertEqual(challenge['expires_at'], 400)
        self.assertFalse(challenge['publishing_enabled'])
        meta, result = self.call(path='/api/v1/auth/google',
            body={'challenge_id': 'b' * 43, 'id_token': 'verified-only-by-server',
                  'tenant_id': 'shop'})
        self.assertEqual(meta['status'], '200 OK')
        self.assertEqual(result['session_token'], 'd' * 43)
        self.assertEqual(self.api.calls[1][1]['server_now'], 100)

    def test_google_login_rejects_untrusted_claims(self):
        meta, _ = self.call(path='/api/v1/auth/google',
            body={'challenge_id': 'b' * 43, 'id_token': 'x' * 24,
                  'tenant_id': 'shop', 'email_verified': True})
        self.assertEqual(meta['status'], '400 Bad Request')
        self.assertEqual(self.api.calls, [])

    def test_server_rejects_untrusted_session_result(self):
        self.api.password_login = lambda **kwargs: {
            'session_token': 'not-a-real-token', 'publishing_enabled': True}
        meta, result = self.call()
        self.assertEqual(meta['status'], '503 Service Unavailable')
        self.assertNotIn('session_token', result)


class RealIdentityGatewayTests(unittest.TestCase):
    def test_password_login_uses_verified_identity_and_membership(self):
        from accounts import AccountDirectory
        from sessions import SessionStore
        from identity_auth import IdentityAuth
        from login_throttle import LoginThrottle
        from auth_login_api import AuthLoginAPI

        db = sqlite3.connect(':memory:')
        try:
            directory = AccountDirectory(db)
            sessions = SessionStore(db)
            identities = IdentityAuth(db, sessions, directory)
            subject = identities.register_password(
                email='owner@example.com',
                password='correct horse battery staple', now=100)
            identities.set_email_verified_trusted(
                subject_id=subject, verified=True)
            directory.bootstrap_owner('shop', subject)
            api = AuthLoginAPI(
                auth=identities, google_verifier=None, challenges=None,
                throttle=LoginThrottle(db))
            app = BAMAuthWSGI(api, enabled=True, clock=lambda: 101)
            basic = BAMAuthWSGITests()
            basic.api = api
            basic.app = app
            _, result = basic.call()
            self.assertIsNotNone(
                sessions.resolve_current(result['session_token'],
                                         directory=directory, now=102))
            meta, denied = basic.call(body={
                'email': 'owner@example.com',
                'password': 'correct horse battery staple',
                'tenant_id': 'other'})
            self.assertEqual(meta['status'], '401 Unauthorized')
            self.assertNotIn('session_token', denied)
        finally:
            db.close()


if __name__ == '__main__':
    unittest.main()
