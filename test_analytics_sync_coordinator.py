import sqlite3
import unittest
from analytics_import_boundary import AnalyticsImportBoundary
from audience_observation_store import AudienceObservationStore
from analytics_sync_coordinator import AnalyticsSyncCoordinator

class AnalyticsSyncTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.store=AudienceObservationStore(self.db)
        self.importer=AnalyticsImportBoundary(store=self.store,
            account_bindings={('shop','facebook'):'page'},
            import_secrets={('shop','facebook'):'secret'})
        self.sync=AnalyticsSyncCoordinator(db=self.db,importer=self.importer)
        self.item=dict(source_post_id='p1',candidate='morning',
                       engagement_count=10,impression_count=100,measured_at=100)
        self.params=dict(tenant_id='shop',platform='facebook',account_id='page',
                         import_secret='secret',expected_cursor=None,
                         next_cursor='cursor1',observations=[self.item],now=101)

    def apply(self,**changes):
        args=dict(self.params)
        args.update(changes)
        return self.sync.apply_batch(**args)

    def test_success_advances_checkpoint(self):
        self.assertEqual(self.apply()['imported'],1)
        self.assertEqual(self.sync.checkpoint(tenant_id='shop',
            platform='facebook',account_id='page')['cursor'],'cursor1')

    def test_bad_secret_never_changes_state(self):
        with self.assertRaises(PermissionError):
            self.apply(import_secret='bad')
        self.assertIsNone(self.sync.checkpoint(tenant_id='shop',
            platform='facebook',account_id='page'))

    def test_stale_cursor_denied(self):
        self.apply()
        with self.assertRaises(ValueError):
            self.apply(next_cursor='cursor2')

    def test_duplicate_batch_rolls_back_checkpoint(self):
        self.apply()
        with self.assertRaises(sqlite3.IntegrityError):
            self.apply(expected_cursor='cursor1',next_cursor='cursor2')
        self.assertEqual(self.sync.checkpoint(tenant_id='shop',
            platform='facebook',account_id='page')['cursor'],'cursor1')

    def test_partial_batch_failure_rolls_back_all(self):
        duplicate=dict(self.item,source_post_id='p1')
        with self.assertRaises(sqlite3.IntegrityError):
            self.apply(observations=[self.item,duplicate])
        self.assertIsNone(self.sync.checkpoint(tenant_id='shop',
            platform='facebook',account_id='page'))
        self.assertEqual(self.store.for_candidates(tenant_id='shop',
            platform='facebook',candidates=['morning'],since=0,until=200),[])

    def test_invalid_batch_denied(self):
        with self.assertRaises(ValueError):
            self.apply(observations=[])

    def test_commit_guard_rejects_and_rolls_back_all_observations(self):
        checked=[]
        def revoked():
            checked.append(True)
            raise PermissionError('Simulated permission change')
        with self.assertRaises(PermissionError):
            self.apply(admission_guard=revoked)
        self.assertEqual(checked,[True])
        self.assertIsNone(self.sync.checkpoint(tenant_id='shop',
            platform='facebook',account_id='page'))
        self.assertEqual(self.store.for_candidates(tenant_id='shop',
            platform='facebook',candidates=['morning'],
            since=0,until=200),[])
        self.assertEqual(self.apply(admission_guard=lambda:None)['imported'],1)

    def test_invalid_guard_cannot_be_accepted(self):
        with self.assertRaises(TypeError):
            self.apply(admission_guard='client supplied')

    def test_cross_tenant_denied(self):
        with self.assertRaises(PermissionError):
            self.apply(tenant_id='other')

if __name__=='__main__':unittest.main()
