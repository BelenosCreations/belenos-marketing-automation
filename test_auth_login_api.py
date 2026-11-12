import sqlite3
import unittest
from accounts import AccountDirectory
from sessions import SessionStore
from identity_auth import IdentityAuth
from google_token_verifier import GoogleTokenVerifier
from google_login_challenges import GoogleLoginChallenges
from auth_login_api import AuthLoginAPI
from login_throttle import LoginThrottle
from business_invitations import BusinessInvitations
from access_policy import Role

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

    def test_opt_in_password_invite_redemption_requires_shared_throttle(self):
        owner_session=self.password()
        guest=self.auth.register_password(email='guest@example.com',
            password='guest password phrase 123',now=100)
        self.auth.set_email_verified_trusted(subject_id=guest,verified=True)
        delivered=[]
        invites=BusinessInvitations(db=self.db,sessions=self.sessions,
            directory=self.directory,auth=self.auth,
            deliver=lambda email,tenant,secret:delivered.append(secret))
        invites.invite(owner_session=owner_session,tenant_id='shop',
            email='guest@example.com',role=Role.VIEWER,now=103)
        self.assertIsNone(self.directory.resolve('shop',guest))
        with self.assertRaises(PermissionError):
            self.api.redeem_invitation_password(
                email='guest@example.com',password='guest password phrase 123',
                token=delivered[-1],server_now=104)
        with self.assertRaises(ValueError):
            AuthLoginAPI(auth=self.auth,google_verifier=self.verifier,
                challenges=self.challenges,invitations=invites,
                allow_invitation_redemption=True)
        with self.assertRaises(ValueError):
            AuthLoginAPI(auth=self.auth,google_verifier=self.verifier,
                challenges=self.challenges,allow_invitation_redemption=1)
        gate=AuthLoginAPI(auth=self.auth,google_verifier=self.verifier,
            challenges=self.challenges,invitations=invites,
            throttle=LoginThrottle(self.db,max_failures=2,window_seconds=60),
            allow_invitation_redemption=True)
        for t in (104,105):
            with self.assertRaises(PermissionError):
                gate.redeem_invitation_password(email='guest@example.com',
                    password='wrong password phrase 123',
                    token=delivered[-1],server_now=t)
        with self.assertRaises(PermissionError):
            gate.redeem_invitation_password(email='guest@example.com',
                password='guest password phrase 123',
                token=delivered[-1],server_now=106)
        self.assertIsNone(self.directory.resolve('shop',guest))
        accepted=gate.redeem_invitation_password(
            email='guest@example.com',password='guest password phrase 123',
            token=delivered[-1],server_now=167)
        self.assertTrue(accepted['membership_created'])
        self.assertIsNone(accepted['session_token'])
        self.assertNotIn(delivered[-1],str(accepted))
        self.assertEqual(self.directory.resolve('shop',guest).role,Role.VIEWER)
        self.assertIsNone(self.directory.resolve('other',guest))
        self.assertIsNotNone(self.auth.login_password(
            email='guest@example.com',password='guest password phrase 123',
            tenant_id='shop',now=168))
        with self.assertRaises(PermissionError):
            gate.redeem_invitation_password(
                email='guest@example.com',password='guest password phrase 123',
                token=delivered[-1],server_now=169)

    def test_password_login_throttles_failures(self):
        self.api.throttle=LoginThrottle(self.db,max_failures=2,window_seconds=60)
        for _ in range(2):
            with self.assertRaises(PermissionError):
                self.api.password_login(email='owner@example.com',
                    password='incorrect passphrase here',tenant_id='shop',
                    server_now=102)
        with self.assertRaises(PermissionError):
            self.api.password_login(email='owner@example.com',
                password='correct horse battery staple',tenant_id='shop',
                server_now=103)
        result=self.api.password_login(email='owner@example.com',
            password='correct horse battery staple',tenant_id='shop',
            server_now=163)
        self.assertIn('session_token',result)

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
