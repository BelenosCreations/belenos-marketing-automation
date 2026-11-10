import sqlite3
import unittest
from editorial_attestations import EditorialAttestations

class AttestationTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.store=EditorialAttestations(self.db)
        self.args=dict(tenant_id='belenos',original_url='https://example.org/post',
                       platform='youtube',account_id='maker',identity_verified=True,
                       competitor_status='cleared',verified_at=100,expires_at=200)

    def test_valid_attestation(self):
        self.store.record_trusted(**self.args)
        self.assertTrue(self.store.resolve(tenant_id='belenos',original_url=self.args['original_url'],now=101)['identity_verified'])

    def test_other_tenant_cannot_reuse(self):
        self.store.record_trusted(**self.args)
        self.assertIsNone(self.store.resolve(tenant_id='busy_b',original_url=self.args['original_url'],now=101))

    def test_expiry(self):
        self.store.record_trusted(**self.args)
        self.assertIsNone(self.store.resolve(tenant_id='belenos',original_url=self.args['original_url'],now=200))

    def test_future_attestation_not_valid(self):
        self.store.record_trusted(**self.args)
        self.assertIsNone(self.store.resolve(tenant_id='belenos',original_url=self.args['original_url'],now=99))

    def test_boolean_required(self):
        with self.assertRaises(ValueError):
            self.store.record_trusted(**dict(self.args,identity_verified=1))

    def test_invalid_competitor_status_rejected(self):
        with self.assertRaises(ValueError):
            self.store.record_trusted(**dict(self.args,competitor_status='safe'))

    def test_invalid_lifetime_rejected(self):
        with self.assertRaises(ValueError):
            self.store.record_trusted(**dict(self.args,expires_at=100))

    def test_revocation_by_new_attestation(self):
        self.store.record_trusted(**self.args)
        self.store.record_trusted(**dict(self.args,identity_verified=False,competitor_status='possible'))
        self.assertFalse(self.store.resolve(tenant_id='belenos',original_url=self.args['original_url'],now=101)['identity_verified'])

    def test_overlong_attestation_rejected(self):
        with self.assertRaises(ValueError):
            self.store.record_trusted(
                tenant_id='shop',original_url='https://example.org/post',
                platform='youtube',account_id='maker',
                identity_verified=True,competitor_status='cleared',
                verified_at=100,expires_at=100+86401)

if __name__=='__main__':unittest.main()
