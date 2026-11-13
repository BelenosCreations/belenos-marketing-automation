"""No remotely addressed request can use offline authentication or assets."""
import json
import sqlite3
import unittest
from bam_offline_gateway import BAMOfflineGateway
from bam_offline_network_guard import offline_gateway_request_allowed

class OfflineNetworkGuardTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.app=BAMOfflineGateway(self.db,enabled=True,clock=lambda:101,
            serve_browser_assets=True,
            trusted_invitation_delivery=lambda *args:None,
            enable_invitation_issuing=True,enable_invitation_acceptance=True)
    def tearDown(self):
        self.db.close()
    def call(self,path,**opts):
        env={'PATH_INFO':path,'REQUEST_METHOD':'GET',
             'wsgi.url_scheme':'https'}
        env.update(opts)
        got={}
        raw=b''.join(self.app(env,lambda status,headers:
            got.update(status=status,headers=dict(headers))))
        return got,raw

    def test_unrecognized_proxy_and_ambiguous_http_framing_denied(self):
        for metadata in (
            {'HTTP_X_FORWARDED_PREFIX':'/external'},
            {'HTTP_X_ORIGINAL_URI':'/api/v1/auth/password'},
            {'HTTP_TRANSFER_ENCODING':'chunked'},
            {'HTTP_CONTENT_LENGTH':'42'},
            {'HTTP_X_HTTP_METHOD_OVERRIDE':'POST'},
            {'HTTP_CF_CONNECTING_IP':'192.0.2.7'},
            {'HTTP_PROXY':'http://proxy.local'},
            {123:'not-a-wsgi-name'}):
            with self.subTest(metadata=metadata):
                self.assertFalse(offline_gateway_request_allowed(metadata))
                if all(type(k) is str for k in metadata):
                    self.assertEqual(self.call('/api/v1/dashboard',
                        **metadata)[0]['status'],'403 Forbidden')

    def test_normal_offline_fixtures_and_loopback(self):
        self.assertTrue(offline_gateway_request_allowed({}))
        for authority in ('localhost','LOCALHOST:443','127.0.0.1:8080',
                          '[::1]','[::1]:443'):
            self.assertTrue(offline_gateway_request_allowed({
                'HTTP_HOST':authority,'REMOTE_ADDR':'127.0.0.1'}))
        self.assertTrue(offline_gateway_request_allowed({
            'HTTP_HOST':'[::1]','SERVER_NAME':'::1','REMOTE_ADDR':'::1'}))
        self.assertEqual(self.call('/api/v1/dashboard',
            HTTP_HOST='localhost:8080',
            REMOTE_ADDR='127.0.0.1')[0]['status'],'401 Unauthorized')

    def test_network_and_proxy_attacks_block_all_routes(self):
        hostile=[
            {'REMOTE_ADDR':'203.0.113.7','HTTP_HOST':'localhost'},
            {'REMOTE_ADDR':'192.0.2.9','HTTP_HOST':'127.0.0.1'},
            {'HTTP_HOST':'bam.example.com'},
            {'HTTP_HOST':'localhost.evil.com'},
            {'HTTP_HOST':'localhost:99999'},
            {'HTTP_HOST':'localhost:0'},
            {'HTTP_HOST':'127.0.0.1@evil.com'},
            {'HTTP_HOST':'http://localhost'},
            {'HTTP_HOST':'127.0.0.1,other.example'},
            {'HTTP_HOST':'[::1].evil'},
            {'SERVER_NAME':'0.0.0.0'},
            {'SERVER_NAME':'public.example'},
            {'REMOTE_ADDR':'::ffff:127.0.0.1'},
            {'HTTP_X_FORWARDED_FOR':'198.51.100.2'},
            {'HTTP_X_FORWARDED_HOST':'public.example'},
            {'HTTP_X_FORWARDED_PROTO':'https'},
            {'HTTP_FORWARDED':'for=198.51.100.2'},
            {'HTTP_X_REAL_IP':'198.51.100.3'},
        ]
        paths=('/api/v1/dashboard',
               '/api/v1/team/invitations/accept-password',
               '/api/v1/team/invitations/create',
               '/ui/bam_signed_in_shell.html')
        for params in hostile:
            with self.subTest(params=params):
                self.assertFalse(offline_gateway_request_allowed(params))
                for path in paths:
                    meta,raw=self.call(path,**params)
                    self.assertEqual(meta['status'],'403 Forbidden')
                    self.assertEqual(meta['headers']['Cache-Control'],
                                     'no-store, private')
                    self.assertEqual(json.loads(raw)['error'],
                                     'Offline gateway is local-only')
    def test_malformed_metadata_never_grants_access(self):
        for env in (None,[],True,{'REMOTE_ADDR':None},
                    {'HTTP_HOST':False}):
            self.assertFalse(offline_gateway_request_allowed(env))
        self.assertFalse(offline_gateway_request_allowed(
            {'REMOTE_ADDR':'198.51.100.1','allow_external':True}))

if __name__=='__main__':
    unittest.main()
