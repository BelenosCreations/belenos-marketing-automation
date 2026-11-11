import sqlite3
import unittest
from accounts import AccountDirectory
from sessions import SessionStore
from identity_auth import IdentityAuth
from email_credential_recovery import EmailCredentialRecovery

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.directory=AccountDirectory(self.db)
        self.sessions=SessionStore(self.db)
        self.auth=IdentityAuth(self.db,self.sessions,self.directory)
        self.subject=self.auth.register_password(email='owner@example.com',
            password='correct horse battery staple',now=100)
        self.directory.bootstrap_owner('shop',self.subject)
        self.outbox=[]
        self.recovery=EmailCredentialRecovery(db=self.db,auth=self.auth,
            deliver=lambda email,purpose,token:self.outbox.append((email,purpose,token)))

    def verify(self):
        self.recovery.request(email='owner@example.com',purpose='verify',now=100)
        token=self.outbox[-1][2]
        self.recovery.confirm_email(token=token,now=101)

    def test_verify_enables_password_login(self):
        self.verify()
        token=self.auth.login_password(email='owner@example.com',
            password='correct horse battery staple',tenant_id='shop',now=102)
        self.assertIsNotNone(self.sessions.resolve(token,now=103))

    def test_verify_one_time_and_expiry(self):
        self.recovery.request(email='owner@example.com',purpose='verify',now=100)
        token=self.outbox[-1][2]
        with self.assertRaises(PermissionError):
            self.recovery.confirm_email(token=token,now=1000)
        self.recovery.confirm_email(token=token,now=101)
        with self.assertRaises(PermissionError):
            self.recovery.confirm_email(token=token,now=102)

    def test_reset_revokes_sessions(self):
        self.verify()
        token=self.auth.login_password(email='owner@example.com',
            password='correct horse battery staple',tenant_id='shop',now=102)
        self.recovery.request(email='owner@example.com',purpose='reset',now=103)
        reset_token=self.outbox[-1][2]
        self.recovery.reset_password(token=reset_token,
            new_password='replacement passphrase 12345',now=104)
        self.assertIsNone(self.sessions.resolve(token,now=105))
        with self.assertRaises(PermissionError):
            self.recovery.reset_password(token=reset_token,
                new_password='yet another replacement 6789',now=105)
        replacement=self.auth.login_password(email='owner@example.com',
            password='replacement passphrase 12345',tenant_id='shop',now=105)
        self.assertIsNotNone(self.sessions.resolve(replacement,now=106))

    def test_nonexistent_email_generic_response(self):
        result=self.recovery.request(email='nobody@example.com',
            purpose='reset',now=101)
        self.assertEqual(result,{'request_accepted':True})
        self.assertEqual(self.outbox,[])

    def test_reset_unverified_email_not_sent(self):
        self.recovery.request(email='owner@example.com',purpose='reset',now=101)
        self.assertEqual(self.outbox,[])

    def test_token_not_stored_plaintext(self):
        self.recovery.request(email='owner@example.com',purpose='verify',now=101)
        token=self.outbox[-1][2]
        stored=self.db.execute('SELECT token_hash FROM bam_email_actions').fetchone()[0]
        self.assertNotEqual(token,stored)

if __name__=='__main__':unittest.main()
