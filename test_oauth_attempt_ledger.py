import sqlite3
import unittest
from oauth_attempt_ledger import OAuthAttemptLedger

class OAuthAttemptLedgerTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.ledger=OAuthAttemptLedger(self.db)
        self.attempt=self.ledger.begin_trusted(
            tenant_id='shop',platform='facebook',account_id='page',
            now=100,ttl_seconds=300)
        self.args=dict(tenant_id='shop',platform='facebook',account_id='page',
            state=self.attempt['state'],
            code_verifier=self.attempt['code_verifier'],now=101)

    def consume(self,**changes):
        args=dict(self.args)
        args.update(changes)
        return self.ledger.consume_trusted(**args)

    def test_valid_state_one_time(self):
        self.assertTrue(self.consume()['state_verified'])
        with self.assertRaises(PermissionError):
            self.consume()

    def test_wrong_tenant_rejected(self):
        with self.assertRaises(PermissionError):
            self.consume(tenant_id='other')

    def test_wrong_account_rejected(self):
        with self.assertRaises(PermissionError):
            self.consume(account_id='other')

    def test_wrong_platform_rejected(self):
        with self.assertRaises(PermissionError):
            self.consume(platform='instagram')

    def test_expired_rejected(self):
        with self.assertRaises(PermissionError):
            self.consume(now=400)

    def test_wrong_verifier_rejected(self):
        with self.assertRaises(PermissionError):
            self.consume(code_verifier='x'*64)

    def test_unknown_state_rejected(self):
        with self.assertRaises(PermissionError):
            self.consume(state='a'*48)

    def test_pkce_challenge_matches_verifier(self):
        import base64,hashlib
        expected=base64.urlsafe_b64encode(hashlib.sha256(
            self.attempt['code_verifier'].encode('ascii')).digest()
        ).decode('ascii').rstrip('=')
        self.assertEqual(self.attempt['code_challenge'],expected)

    def test_does_not_store_raw_secrets(self):
        row=self.db.execute('SELECT state_hash,verifier_hash FROM oauth_attempts').fetchone()
        self.assertNotEqual(row[0],self.attempt['state'])
        self.assertNotEqual(row[1],self.attempt['code_verifier'])

    def test_invalid_ttl(self):
        with self.assertRaises(ValueError):
            self.ledger.begin_trusted(tenant_id='shop',platform='facebook',
                account_id='page',now=100,ttl_seconds=1)

if __name__=='__main__':unittest.main()
