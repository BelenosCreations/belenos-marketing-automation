import sqlite3
import unittest
from datetime import datetime, timezone
from analytics_import_boundary import AnalyticsImportBoundary
from analytics_sync_coordinator import AnalyticsSyncCoordinator
from audience_observation_store import AudienceObservationStore
from analytics_page_adapter import AnalyticsPageAdapter

class Fetcher:
    def __init__(self,page):
        self.page=page
        self.calls=0
        self.cursor_seen=None
    def fetch_page(self,*,tenant_id,platform,account_id,cursor):
        self.calls+=1
        self.cursor_seen=cursor
        return self.page

class AnalyticsPageAdapterTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.store=AudienceObservationStore(self.db)
        importer=AnalyticsImportBoundary(store=self.store,
            account_bindings={('shop','facebook'):'page'},
            import_secrets={('shop','facebook'):'secret'})
        self.sync=AnalyticsSyncCoordinator(db=self.db,importer=importer)
        self.published=int(datetime(2026,11,9,15,tzinfo=timezone.utc).timestamp())
        self.fetcher=Fetcher(dict(next_cursor='next1',posts=[
            dict(post_id='post1',published_at=self.published,
                 engagement_count=20,impression_count=100)]))
        self.adapter=AnalyticsPageAdapter(coordinator=self.sync,
            fetcher=self.fetcher,
            account_bindings={('shop','facebook'):'page'},
            timezone_by_tenant={'shop':'America/New_York'})
        self.params=dict(tenant_id='shop',platform='facebook',
                         account_id='page',import_secret='secret',
                         now=self.published+3600)

    def test_preview_does_not_write(self):
        result=self.adapter.preview_import(**self.params)
        self.assertEqual(result['observations'][0]['candidate'],'0:10')
        self.assertIsNone(self.sync.checkpoint(tenant_id='shop',
            platform='facebook',account_id='page'))

    def test_import_advances_checkpoint(self):
        result=self.adapter.import_page(**self.params)
        self.assertEqual(result['imported'],1)
        self.assertEqual(self.sync.checkpoint(tenant_id='shop',
            platform='facebook',account_id='page')['cursor'],'next1')

    def test_unauthorized_caller_cannot_fetch(self):
        with self.assertRaises(PermissionError):
            self.adapter.import_page(**dict(self.params,import_secret='bad'))
        self.assertEqual(self.fetcher.calls,0)

    def test_other_tenant_cannot_fetch(self):
        with self.assertRaises(PermissionError):
            self.adapter.import_page(**dict(self.params,tenant_id='other'))
        self.assertEqual(self.fetcher.calls,0)

    def test_future_post_rejected(self):
        self.fetcher.page['posts'][0]['published_at']=self.params['now']+1
        with self.assertRaises(ValueError):
            self.adapter.import_page(**self.params)

    def test_malformed_page_rejected(self):
        self.fetcher.page={'next_cursor':'next1','posts':[]}
        with self.assertRaises(ValueError):
            self.adapter.import_page(**self.params)

    def test_bad_account_binding_denied(self):
        self.adapter.account_bindings[('shop','facebook')]='wrong'
        with self.assertRaises(PermissionError):
            self.adapter.import_page(**self.params)

if __name__=='__main__':unittest.main()
