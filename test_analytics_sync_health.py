import sqlite3
import unittest
from analytics_import_boundary import AnalyticsImportBoundary
from analytics_sync_coordinator import AnalyticsSyncCoordinator
from audience_observation_store import AudienceObservationStore
from analytics_sync_health import assess_sync_health

class SyncHealthTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.store=AudienceObservationStore(self.db)
        self.importer=AnalyticsImportBoundary(store=self.store,
            account_bindings={('shop','facebook'):'page'},
            import_secrets={('shop','facebook'):'secret'})
        self.coordinator=AnalyticsSyncCoordinator(db=self.db,
                                                  importer=self.importer)
        self.args=dict(coordinator=self.coordinator,importer=self.importer,
            tenant_id='shop',platform='facebook',account_id='page',
            import_secret='secret',now=100000,max_checkpoint_age=100)

    def health(self,**changes):
        args=dict(self.args)
        args.update(changes)
        return assess_sync_health(**args)

    def checkpoint(self,updated):
        self.db.execute("""INSERT INTO analytics_sync_checkpoints
            (tenant_id,platform,account_id,cursor,updated_at)
            VALUES ('shop','facebook','page','cursor',?)""",(updated,))
        self.db.commit()

    def test_missing_checkpoint(self):
        self.assertEqual(self.health()['status'],'not_started')

    def test_current_checkpoint(self):
        self.checkpoint(99950)
        self.assertEqual(self.health()['status'],'current')

    def test_stale_checkpoint(self):
        self.checkpoint(99899)
        result=self.health()
        self.assertEqual(result['status'],'stale')
        self.assertEqual(result['action'],'review_provider_connection')

    def test_future_checkpoint_invalid(self):
        self.checkpoint(100001)
        self.assertEqual(self.health()['status'],'invalid_checkpoint')

    def test_bad_secret_denied(self):
        with self.assertRaises(PermissionError):
            self.health(import_secret='wrong')

    def test_other_tenant_denied(self):
        with self.assertRaises(PermissionError):
            self.health(tenant_id='other')

    def test_invalid_threshold_denied(self):
        with self.assertRaises(ValueError):
            self.health(max_checkpoint_age=0)

    def test_never_publishes(self):
        self.assertFalse(self.health()['publishing_enabled'])

if __name__=='__main__':unittest.main()
