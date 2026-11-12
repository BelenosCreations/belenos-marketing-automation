import sqlite3
import unittest
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from identity_auth import IdentityAuth,normalize_email

class IdentityAuthTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.directory=AccountDirectory(self.db)
        self.sessions=SessionStore(self.db)
        self.auth=IdentityAuth(self.db,self.sessions,self.directory)
        self.subject=self.auth.register_password(email='Owner@Example.com',
            password='correct horse battery staple',now=100)
        self.directory.bootstrap_owner('shop',self.subject)

    def verify(self):
        self.auth.set_email_verified_trusted(subject_id=self.subject,verified=True)

    def test_registration_does_not_grant_login(self):
        with self.assertRaises(PermissionError):
            self.auth.login_password(email='owner@example.com',
                password='correct horse battery staple',tenant_id='shop',now=101)

    def test_password_login_after_email_verification(self):
        self.verify()
        token=self.auth.login_password(email='OWNER@example.com',
            password='correct horse battery staple',tenant_id='shop',now=101)
        self.assertEqual(self.sessions.resolve_current(token,
            directory=self.directory,now=102).principal.subject_id,self.subject)

    def test_wrong_password_and_unknown_email(self):
        self.verify()
        for email,password in [('owner@example.com','incorrect password'),
                               ('nobody@example.com','correct horse battery staple')]:
            with self.assertRaises(PermissionError):
                self.auth.login_password(email=email,password=password,
                                         tenant_id='shop',now=101)

    def test_trusted_password_verification_without_membership_creates_no_session(self):
        guest=self.auth.register_password(email='guest@example.com',
            password='guest password phrase 123',now=101)
        self.auth.set_email_verified_trusted(subject_id=guest,verified=True)
        self.assertEqual(self.auth.verify_password_identity_trusted(
            email='GUEST@example.com',password='guest password phrase 123'),guest)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM sessions')
                         .fetchone()[0],0)
        with self.assertRaises(PermissionError):
            self.auth.login_password(email='guest@example.com',
                password='guest password phrase 123',tenant_id='shop',now=102)
        for email,password in (
            ('guest@example.com','incorrect phrase 12345'),
            ('another@example.com','guest password phrase 123')
        ):
            with self.assertRaises(PermissionError):
                self.auth.verify_password_identity_trusted(
                    email=email,password=password)
        self.auth.set_email_verified_trusted(subject_id=guest,verified=False)
        with self.assertRaises(PermissionError):
            self.auth.verify_password_identity_trusted(
                email='guest@example.com',password='guest password phrase 123')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM sessions')
                         .fetchone()[0],0)

    def test_no_cross_tenant_membership(self):
        self.verify()
        with self.assertRaises(PermissionError):
            self.auth.login_password(email='owner@example.com',
                password='correct horse battery staple',tenant_id='other',now=101)

    def test_password_not_stored_plaintext(self):
        raw=self.db.execute('SELECT salt,digest FROM bam_password_credentials').fetchone()
        self.assertEqual(len(raw[0]),32)
        self.assertEqual(len(raw[1]),32)
        self.assertNotIn(b'correct horse',raw[1])

    def test_no_google_auto_link_from_matching_email(self):
        self.verify()
        with self.assertRaises(PermissionError):
            self.auth.login_google_verified(google_sub='google-1',
                email='owner@example.com',email_verified=True,
                tenant_id='shop',now=101)

    def test_google_link_requires_verified_bam_identity(self):
        with self.assertRaises(PermissionError):
            self.auth.link_google_verified(subject_id=self.subject,
                google_sub='google-1',email='owner@example.com',email_verified=True)
        self.verify()
        with self.assertRaises(PermissionError):
            self.auth.link_google_verified(subject_id=self.subject,
                google_sub='google-1',email='owner@example.com',email_verified=False)

    def test_linked_google_login(self):
        self.verify()
        self.auth.link_google_verified(subject_id=self.subject,google_sub='google-1',
            email='owner@example.com',email_verified=True)
        token=self.auth.login_google_verified(google_sub='google-1',
            email='owner@example.com',email_verified=True,tenant_id='shop',now=101)
        self.assertEqual(self.sessions.resolve(token,now=102).principal.subject_id,
                         self.subject)

    def test_registered_google_identity_is_bound_without_a_business_session(self):
        guest=self.auth.register_google_verified(
            google_sub='registered-google-guest',
            email='google-guest@example.com',email_verified=True,now=101)
        linked=self.db.execute("""SELECT subject_id FROM bam_google_identities
            WHERE google_sub='registered-google-guest'""").fetchone()
        self.assertEqual(linked[0],guest)
        self.assertEqual(self.auth.verify_google_identity_trusted(
            google_sub='registered-google-guest',
            email='google-guest@example.com',email_verified=True),guest)
        self.assertIsNone(self.directory.resolve('shop',guest))
        with self.assertRaises(PermissionError):
            self.auth.login_google_verified(
                google_sub='registered-google-guest',
                email='google-guest@example.com',email_verified=True,
                tenant_id='shop',now=102)
        for sub,email,verified in (
            ('different-google','google-guest@example.com',True),
            ('registered-google-guest','other@example.com',True),
            ('registered-google-guest','google-guest@example.com',False)
        ):
            with self.assertRaises(PermissionError):
                self.auth.verify_google_identity_trusted(
                    google_sub=sub,email=email,email_verified=verified)
        before=self.db.execute('SELECT COUNT(*) FROM bam_identities').fetchone()[0]
        with self.assertRaises(sqlite3.IntegrityError):
            self.auth.register_google_verified(google_sub='registered-google-guest',
                email='different-email@example.com',email_verified=True,now=102)
        self.assertEqual(self.db.execute(
            'SELECT COUNT(*) FROM bam_identities').fetchone()[0],before)
        self.assertEqual(self.db.execute(
            'SELECT COUNT(*) FROM sessions').fetchone()[0],0)

    def test_google_subject_mismatch_denied(self):
        self.verify()
        self.auth.link_google_verified(subject_id=self.subject,google_sub='google-1',
            email='owner@example.com',email_verified=True)
        for sub,email,verified in [
                ('google-2','owner@example.com',True),
                ('google-1','attacker@example.com',True),
                ('google-1','owner@example.com',False)]:
            with self.assertRaises(PermissionError):
                self.auth.login_google_verified(google_sub=sub,email=email,
                    email_verified=verified,tenant_id='shop',now=101)

    def test_duplicate_email_denied(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.auth.register_password(email='OWNER@example.com',
                password='another valid passphrase',now=101)

    def test_identity_disable_revokes_sessions(self):
        self.verify()
        token=self.auth.login_password(email='owner@example.com',
            password='correct horse battery staple',tenant_id='shop',now=101)
        self.auth.disable_identity_trusted(subject_id=self.subject,now=102)
        self.assertIsNone(self.sessions.resolve(token,now=103))
        with self.assertRaises(PermissionError):
            self.auth.login_password(email='owner@example.com',
                password='correct horse battery staple',tenant_id='shop',now=104)

    def test_rotation_revokes_sessions(self):
        self.verify()
        first=self.auth.login_password(email='owner@example.com',
            password='correct horse battery staple',tenant_id='shop',now=101)
        second=self.auth.login_password(email='owner@example.com',
            password='correct horse battery staple',tenant_id='shop',now=101)
        self.auth.change_password(session_token=first,
            current_password='correct horse battery staple',
            new_password='replacement passphrase 12345',now=102)
        self.assertIsNone(self.sessions.resolve(first,now=103))
        self.assertIsNone(self.sessions.resolve(second,now=103))
        replacement=self.auth.login_password(email='owner@example.com',
            password='replacement passphrase 12345',tenant_id='shop',now=103)
        self.assertIsNotNone(self.sessions.resolve(replacement,now=104))

    def test_password_policy(self):
        with self.assertRaises(ValueError):
            self.auth.register_password(email='short@example.com',
                password='short',now=101)
        with self.assertRaises(ValueError):
            normalize_email('invalid')

if __name__=='__main__':unittest.main()
