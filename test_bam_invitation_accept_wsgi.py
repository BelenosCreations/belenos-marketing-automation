
"""Offline integration tests: explicitly opted-in invitation acceptance."""
import io
import json
import sqlite3
import unittest

from access_policy import Role
from bam_offline_gateway import BAMOfflineGateway
from google_token_verifier import GoogleTokenVerifier


class BAMInvitationAcceptHTTPTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.now=101
        self.outbox=[]
        self.claims={}
        self.verifier=GoogleTokenVerifier(client_id='client-id',
            verify_func=lambda token,audience:self.claims.copy())
        self.app=BAMOfflineGateway(self.db,enabled=True,
            clock=lambda:self.now,google_verifier=self.verifier,
            trusted_invitation_delivery=lambda email,tenant,secret:
                self.outbox.append((email,tenant,secret)),
            enable_invitation_acceptance=True)
        self.owner=self.app.identities.register_password(
            email='owner@example.com',
            password='correct horse battery staple',now=100)
        self.app.identities.set_email_verified_trusted(
            subject_id=self.owner,verified=True)
        self.app.directory.bootstrap_owner('shop',self.owner)
        self.app.directory.bootstrap_owner('other','other_owner')
        self.owner_token=self.app.identities.login_password(
            email='owner@example.com',
            password='correct horse battery staple',
            tenant_id='shop',now=self.now)

    def tearDown(self):
        self.db.close()

    def call(self,path,body,*,method='POST',scheme='https',extra=None,raw=None,
             app=None):
        data=(raw if raw is not None else json.dumps(body).encode('utf-8'))
        env={'PATH_INFO':path,'wsgi.url_scheme':scheme,
             'REQUEST_METHOD':method,'CONTENT_TYPE':'application/json',
             'CONTENT_LENGTH':str(len(data)),'wsgi.input':io.BytesIO(data)}
        if extra:env.update(extra)
        meta={}
        response=b''.join((app or self.app)(env,
            lambda status,headers:meta.update(
                status=status,headers=dict(headers))))
        return meta,json.loads(response)

    def invite(self,email,role=Role.VIEWER):
        self.app.business_invitations.invite(
            owner_session=self.owner_token,tenant_id='shop',
            email=email,role=role,now=self.now)
        return self.outbox[-1][2]

    def test_password_redemption_is_off_by_default_and_requires_delivery(self):
        with self.assertRaises(ValueError):
            BAMOfflineGateway(self.db,enabled=True,
                enable_invitation_acceptance=True)
        with self.assertRaises(ValueError):
            BAMOfflineGateway(self.db,enabled=True,
                enable_invitation_acceptance=1)
        normal=BAMOfflineGateway(self.db,enabled=True,clock=lambda:self.now,
            trusted_invitation_delivery=lambda *args:None)
        path='/api/v1/team/invitations/accept-password'
        self.assertEqual(self.call(path,{},app=normal)[0]['status'],
                         '404 Not Found')
        self.assertEqual(self.call(path,{},scheme='http')[0]['status'],
                         '403 Forbidden')
        self.assertEqual(self.call(path,{},method='GET')[0]['status'],
                         '405 Method Not Allowed')

    def test_password_acceptance_never_leaks_secret_or_session(self):
        guest=self.app.identities.register_password(
            email='guest@example.com',
            password='guest password phrase 123',now=100)
        self.app.identities.set_email_verified_trusted(
            subject_id=guest,verified=True)
        secret=self.invite('guest@example.com',Role.CONTENT_CREATOR)
        path='/api/v1/team/invitations/accept-password'
        body={'email':'guest@example.com',
              'password':'guest password phrase 123',
              'invitation_token':secret}
        self.assertIsNone(self.app.directory.resolve('shop',guest))
        for forged in (
            {**body,'tenant_id':'other'},
            {**body,'subject_id':'other_owner'},
            {**body,'publishing_enabled':True},
            {**body,'role':'owner'}
        ):
            self.assertEqual(self.call(path,forged)[0]['status'],
                             '400 Bad Request')
        self.assertEqual(self.call(path,body,
            extra={'QUERY_STRING':'tenant_id=other'})[0]['status'],
            '400 Bad Request')
        self.assertEqual(self.call(path,body,
            extra={'HTTP_AUTHORIZATION':'Bearer junk'})[0]['status'],
            '400 Bad Request')
        bad_raw=(b'{"email":"guest@example.com",'
            b'"email":"other@example.com",'
            b'"password":"guest password phrase 123",'
            b'"invitation_token":"'+secret.encode()+b'"}')
        self.assertEqual(self.call(path,{},raw=bad_raw)[0]['status'],
                         '400 Bad Request')
        wrong={**body,'password':'different password phrase'}
        self.assertEqual(self.call(path,wrong)[0]['status'],
                         '401 Unauthorized')
        self.assertIsNone(self.app.directory.resolve('shop',guest))
        meta,accepted=self.call(path,body)
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(meta['headers']['Cache-Control'],'no-store, private')
        self.assertEqual(accepted,{'membership_created':True,
            'tenant_id':'shop','role':'content_creator',
            'publishing_enabled':False})
        self.assertNotIn(secret,str(accepted))
        self.assertNotIn(body['password'],str(accepted))
        self.assertNotIn('session_token',accepted)
        self.assertIsNone(self.app.directory.resolve('other',guest))
        self.assertEqual(self.call(path,body)[0]['status'],
                         '401 Unauthorized')
        # Acceptance never authenticated the browser; normal sign-in
        # remains a separate credential exchange.
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM sessions '
            'WHERE subject_id=?',(guest,)).fetchone()[0],0)
        self.assertIsNotNone(self.app.identities.login_password(
            email=body['email'],password=body['password'],
            tenant_id='shop',now=self.now))

    def test_google_acceptance_verifies_nonce_and_subject_without_auto_login(self):
        subject=self.app.identities.register_google_verified(
            google_sub='google-invitee',email='google@example.com',
            email_verified=True,now=100)
        secret=self.invite('google@example.com',Role.EMPLOYEE)
        path='/api/v1/team/invitations/accept-google'
        challenge=self.app.login_api.begin_google(server_now=self.now)
        self.claims={'iss':'https://accounts.google.com',
            'aud':'client-id','exp':400,'iat':100,
            'sub':'unknown-google-sub','email':'google@example.com',
            'email_verified':True,'nonce':challenge['nonce']}
        body={'challenge_id':challenge['challenge_id'],
              'id_token':'x'*24,'invitation_token':secret}
        self.assertEqual(self.call(path,body)[0]['status'],
                         '401 Unauthorized')
        self.assertIsNone(self.app.directory.resolve('shop',subject))
        next_challenge=self.app.login_api.begin_google(server_now=self.now)
        self.claims['sub']='google-invitee'
        self.claims['nonce']=next_challenge['nonce']
        body['challenge_id']=next_challenge['challenge_id']
        meta,accepted=self.call(path,body)
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(accepted['tenant_id'],'shop')
        self.assertEqual(accepted['role'],'employee')
        self.assertFalse(accepted['publishing_enabled'])
        self.assertNotIn('session_token',accepted)
        self.assertNotIn(secret,str(accepted))
        self.assertIsNone(self.app.directory.resolve('other',subject))
        self.assertEqual(self.call(path,body)[0]['status'],
                         '401 Unauthorized')
        self.assertEqual(self.db.execute(
            'SELECT COUNT(*) FROM sessions WHERE subject_id=?',
            (subject,)).fetchone()[0],0)
        another=self.app.login_api.begin_google(server_now=self.now)
        self.claims['nonce']=another['nonce']
        logged=self.app.login_api.google_login(
            challenge_id=another['challenge_id'],id_token='x'*24,
            tenant_id='shop',server_now=self.now)
        self.assertIsNotNone(self.app.sessions.resolve_current(
            logged['session_token'],directory=self.app.directory,
            now=self.now+1))


if __name__=='__main__':
    unittest.main()
