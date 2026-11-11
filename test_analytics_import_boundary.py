import sqlite3
import unittest
from analytics_import_boundary import AnalyticsImportBoundary
from audience_observation_store import AudienceObservationStore

class AnalyticsImportBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.store=AudienceObservationStore(self.db)
        self.boundary=AnalyticsImportBoundary(store=self.store,
            account_bindings={('shop','facebook'):'page123'},
            import_secrets={('shop','facebook'):'server-secret'})
        self.params=dict(tenant_id='shop',platform='facebook',
            account_id='page123',import_secret='server-secret',
            source_post_id='post-1',candidate='morning',
            engagement_count=15,impression_count=100,measured_at=100)

    def run_import(self,**changes):
        params=dict(self.params)
        params.update(changes)
        return self.boundary.import_observation(**params)

    def test_authorized_counts_are_normalized(self):
        self.run_import()
        rows=self.store.for_candidates(tenant_id='shop',platform='facebook',
            candidates=['morning'],since=0,until=200)
        self.assertEqual(rows[0]['engagement_rate'],.15)

    def test_wrong_account_denied(self):
        with self.assertRaises(PermissionError):
            self.run_import(account_id='someone-else')

    def test_wrong_secret_denied(self):
        with self.assertRaises(PermissionError):
            self.run_import(import_secret='wrong')

    def test_other_tenant_denied(self):
        with self.assertRaises(PermissionError):
            self.run_import(tenant_id='other')

    def test_other_platform_denied(self):
        with self.assertRaises(PermissionError):
            self.run_import(platform='instagram')

    def test_impossible_counts_rejected(self):
        with self.assertRaises(ValueError):
            self.run_import(engagement_count=101)

    def test_zero_impressions_rejected(self):
        with self.assertRaises(ValueError):
            self.run_import(impression_count=0)

    def test_duplicate_source_rejected(self):
        self.run_import()
        with self.assertRaises(sqlite3.IntegrityError):
            self.run_import()

    def test_malformed_source_rejected(self):
        with self.assertRaises(ValueError):
            self.run_import(source_post_id='post/invalid')

if __name__=='__main__':unittest.main()
