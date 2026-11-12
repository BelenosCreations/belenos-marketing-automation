"""Two independent SQLite clients verify offline analytics revocation races.

No OAuth, provider network calls, paid requests or executable publishing.
The fake fetcher pauses between initial permission and transactional commit.
"""
import os
import sqlite3
import tempfile
import threading
import unittest

from analytics_import_boundary import AnalyticsImportBoundary
from analytics_sync_coordinator import AnalyticsSyncCoordinator
from analytics_page_adapter import AnalyticsPageAdapter
from audience_observation_store import AudienceObservationStore
from connection_gated_analytics import ConnectionGatedAnalyticsAdapter
from provider_connection_registry import ProviderConnectionRegistry


class PausedFetcher:
    def __init__(self):
        self.started=threading.Event()
        self.resume=threading.Event()
        self.calls=0

    def fetch_page(self, **kwargs):
        self.calls+=1
        self.started.set()
        if not self.resume.wait(timeout=8):
            raise TimeoutError('Offline fetch test did not resume')
        return {'next_cursor':'cursor-test','posts':[{
            'post_id':'post-1','published_at':50,
            'engagement_count':3,'impression_count':10}]}


class OfflineAnalyticsRevocationRaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='bam-social-race-')
        self.file=os.path.join(self.tmp.name,'metadata.db')
        self.db1=sqlite3.connect(self.file,timeout=10,check_same_thread=False)
        self.db2=sqlite3.connect(self.file,timeout=10,check_same_thread=False)
        self.store=AudienceObservationStore(self.db1)
        importer=AnalyticsImportBoundary(
            store=self.store,
            account_bindings={('shop','facebook'):'page'},
            import_secrets={('shop','facebook'):'offline-only'})
        self.sync=AnalyticsSyncCoordinator(db=self.db1,importer=importer)
        self.reg1=ProviderConnectionRegistry(self.db1)
        self.reg2=ProviderConnectionRegistry(self.db2)
        self.meta=dict(tenant_id='shop',platform='facebook',account_id='page',
                       vault_reference='vault/test/shop/page',
                       scope='read_insights',state='connected',
                       expires_at=500,now=100)
        self.reg1.register_trusted(**self.meta)
        self.fetcher=PausedFetcher()
        self.adapter=ConnectionGatedAnalyticsAdapter(
            registry=self.reg1,
            adapter=AnalyticsPageAdapter(
                coordinator=self.sync,fetcher=self.fetcher,
                account_bindings={('shop','facebook'):'page'},
                timezone_by_tenant={'shop':'America/New_York'}))
        self.args=dict(tenant_id='shop',platform='facebook',
                       account_id='page',import_secret='offline-only',
                       now=200)

    def tearDown(self):
        self.fetcher.resume.set()
        self.db2.close()
        self.db1.close()
        self.tmp.cleanup()

    def test_revocation_on_second_client_during_fetch_aborts_commit(self):
        result=[]
        def worker():
            try:
                result.append(self.adapter.import_page(**self.args))
            except Exception as exc:
                result.append(exc)
        t=threading.Thread(target=worker,daemon=True)
        t.start()
        try:
            self.assertTrue(self.fetcher.started.wait(timeout=8),
                            'Fake provider read did not begin')
            # The other SQLite connection revokes this binding while the
            # worker is away collecting a read-only analytics page.
            self.reg2.register_trusted(**dict(self.meta,state='revoked',now=150))
        finally:
            self.fetcher.resume.set()
        t.join(timeout=12)
        self.assertFalse(t.is_alive(),'Offline import thread did not finish')
        self.assertEqual(len(result),1)
        self.assertIsInstance(result[0],PermissionError)
        self.assertEqual(self.fetcher.calls,1)
        self.assertEqual(self.reg1.status(tenant_id='shop',
            platform='facebook',account_id='page',now=200)['status'],
            'revoked')
        self.assertIsNone(self.sync.checkpoint(tenant_id='shop',
            platform='facebook',account_id='page'))
        self.assertEqual(self.db2.execute(
            'SELECT COUNT(*) FROM audience_observations').fetchone()[0],0)

    def test_stale_client_cannot_reopen_revoked_connection(self):
        self.reg2.register_trusted(**dict(self.meta,state='revoked',now=150))
        with self.assertRaises(ValueError):
            self.reg1.register_trusted(**dict(self.meta,state='connected',
                                              now=151))
        with self.assertRaises(PermissionError):
            self.adapter.preview_import(**self.args)
        self.assertEqual(self.fetcher.calls,0)

    def test_nonrevoked_newer_state_wins_over_stale_connected_write(self):
        self.reg2.register_trusted(**dict(self.meta,
            state='refresh_required',now=150))
        with self.assertRaises(ValueError):
            self.reg1.register_trusted(**dict(self.meta,state='connected',
                                              now=125))
        self.assertEqual(self.reg1.status(tenant_id='shop',
            platform='facebook',account_id='page',now=200)['status'],
            'refresh_required')


if __name__=='__main__':
    unittest.main()
