import sqlite3
import unittest
from accounts import AccountDirectory
from sessions import SessionStore
from identity_auth import IdentityAuth
from google_token_verifier import GoogleTokenVerifier
from google_login_challenges import GoogleLoginChallenges
from auth_login_api import AuthLoginAPI

class AuthLoginAPITests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.directory=AccountDirectory(self.db)
        self.sessions=SessionStore(self.db)
        self.auth=IdentityAuth(self.db,self.sessions,self.directory)
        self.subject=self.auth.register_password(email='owner@example.com',
            password='correct horse battery staple',now=100)
        self.auth.set_email_verified_trusted(subject_id=self.subject,verified=True)
        self.directory.bootstrap_owner('shop',self.subject)
        self.challenges=GoogleLoginChallenges(self.db)
        self.claims={}
        def verify(token,audience):
            return self.claims.copy()
        self.verifier=GoogleTokenVerifier(client_id='client-id',verify_func=verify)
        self.api=AuthLoginAPI(auth=self.auth,google_verifier=self.verifier,
                              challenges=self.challenges)

    def challenge(self):
        challenge=self.api.begin_google(server_now=101)
        self.claims={'iss':'https://accounts.google.com','aud':'client-id',
            'exp':400,'iat':100,'sub':'google-sub','email':'owner@example.com',
            'email_verified':True,'nonce':challenge['nonce']}
        return challenge

    def password(self):
        return self.api.password_login(email='owner@example.com',
            password='correct horse battery staple',tenant_id='shop',
            server_now=102)['session_token']

    def test_password_login(self):
        self.assertIsNotNone(self.sessions.resolve(self.password(),now=103))

    def test_google_cannot_auto_link(self):
        challenge=self.challenge()
        with self.assertRaises(PermissionError):
            self.api.google_login(challenge_id=challenge['challenge_id'],
                id_token='x'*24,tenant_id='shop',server_now=102)

    def test_explicit_google_link_and_login(self):
        token=self.password()
        challenge=self.challenge()
        result=self.api.link_google_with_password(session_token=token,
            password='correct horse battery staple',
            challenge_id=challenge['challenge_id'],
            id_token='x'*24,server_now=102)
        self.assertTrue(result['linked'])
        new_challenge=self.challenge()
        logged=self.api.google_login(challenge_id=new_challenge['challenge_id'],
            id_token='x'*24,tenant_id='shop',server_now=103)
        self.assertIsNotNone(self.sessions.resolve(logged['session_token'],now=104))

    def test_google_only_signup_has_no_business_access(self):
        challenge=self.challenge()
        self.claims['sub']='new-google-sub'
        self.claims['email']='newperson@example.com'
        result=self.api.register_google(challenge_id=challenge['challenge_id'],
            id_token='x'*24,server_now=102)
        self.assertTrue(result['business_membership_required'])
        self.assertIsNone(result['session_token'])
        self.assertIsNone(self.directory.resolve('shop',result['subject_id']))
        new_challenge=self.challenge()
        self.claims['sub']='new-google-sub'
        self.claims['email']='newperson@example.com'
        with self.assertRaises(PermissionError):
            self.api.google_login(challenge_id=new_challenge['challenge_id'],
                id_token='x'*24,tenant_id='shop',server_now=103)

    def test_google_signup_never_auto_merges_email(self):
        challenge=self.challenge()
        with self.assertRaises(sqlite3.IntegrityError):
            self.api.register_google(challenge_id=challenge['challenge_id'],
                id_token='x'*24,server_now=102)

    def test_wrong_password_does_not_link(self):
        token=self.password()
        challenge=self.challenge()
        with self.assertRaises(PermissionError):
            self.api.link_google_with_password(session_token=token,
                password='wrong password here',
                challenge_id=challenge['challenge_id'],
                id_token='x'*24,server_now=102)
        with self.assertRaises(PermissionError):
            self.api.google_login(challenge_id=challenge['challenge_id'],
                id_token='x'*24,tenant_id='shop',server_now=103)

    def test_google_challenge_replay(self):
        challenge=self.challenge()
        with self.assertRaises(PermissionError):
            self.api.google_login(challenge_id=challenge['challenge_id'],
                id_token='x'*24,tenant_id='shop',server_now=102)
        with self.assertRaises(PermissionError):
            self.api.google_login(challenge_id=challenge['challenge_id'],
                id_token='x'*24,tenant_id='shop',server_now=102)

    def test_nonce_mismatch_fails(self):
        token=self.password()
        challenge=self.challenge()
        self.claims['nonce']='attacker-nonce'
        with self.assertRaises(PermissionError):
            self.api.link_google_with_password(session_token=token,
                password='correct horse battery staple',
                challenge_id=challenge['challenge_id'],
                id_token='x'*24,server_now=102)

    def test_expired_challenge(self):
        challenge=self.challenge()
        with self.assertRaises(PermissionError):
            self.api.google_login(challenge_id=challenge['challenge_id'],
                id_token='x'*24,tenant_id='shop',server_now=402)

if __name__=='__main__':unittest.main()
