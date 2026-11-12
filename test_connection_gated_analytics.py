import sqlite3
import unittest
from analytics_import_boundary import AnalyticsImportBoundary
from analytics_sync_coordinator import AnalyticsSyncCoordinator
from audience_observation_store import AudienceObservationStore
from analytics_page_adapter import AnalyticsPageAdapter
from provider_connection_registry import ProviderConnectionRegistry
from connection_gated_analytics import ConnectionGatedAnalyticsAdapter

class Fetcher:
    def __init__(self):
        self.calls=0
    def fetch_page(self,**kwargs):
        self.calls+=1
        return dict(next_cursor='cursor',posts=[
            dict(post_id='p1',published_at=50,
                 engagement_count=1,impression_count=10)])

class ConnectionGateTests(unittest.TestCase):
    def setUp(self):
        db=sqlite3.connect(':memory:')
        store=AudienceObservationStore(db)
        importer=AnalyticsImportBoundary(store=store,
            account_bindings={('shop','facebook'):'page'},
            import_secrets={('shop','facebook'):'secret'})
        coordinator=AnalyticsSyncCoordinator(db=db,importer=importer)
        self.fetcher=Fetcher()
        adapter=AnalyticsPageAdapter(coordinator=coordinator,
            fetcher=self.fetcher,
            account_bindings={('shop','facebook'):'page'},
            timezone_by_tenant={'shop':'America/New_York'})
        self.registry=ProviderConnectionRegistry(db)
        self.gate=ConnectionGatedAnalyticsAdapter(adapter=adapter,
                                                   registry=self.registry)
        self.args=dict(tenant_id='shop',platform='facebook',
                       account_id='page',import_secret='secret',now=100)
        self.metadata=dict(tenant_id='shop',platform='facebook',
            account_id='page',vault_reference='vault/shop/page',
            scope='read_insights',state='connected',expires_at=200,now=10)

    def test_unconnected_denied_before_fetch(self):
        with self.assertRaises(PermissionError):
            self.gate.import_page(**self.args)
        self.assertEqual(self.fetcher.calls,0)

    def test_connected_allows_preview(self):
        self.registry.register_trusted(**self.metadata)
        self.assertEqual(self.gate.preview_import(**self.args)['status'],'preview')
        self.assertEqual(self.fetcher.calls,1)

    def test_connected_allows_import(self):
        self.registry.register_trusted(**self.metadata)
        self.assertEqual(self.gate.import_page(**self.args)['imported'],1)

    def test_expired_denied(self):
        self.registry.register_trusted(**dict(self.metadata,expires_at=100))
        with self.assertRaises(PermissionError):
            self.gate.import_page(**self.args)
        self.assertEqual(self.fetcher.calls,0)

    def test_revoked_denied(self):
        self.registry.register_trusted(**dict(self.metadata,state='revoked'))
        with self.assertRaises(PermissionError):
            self.gate.import_page(**self.args)
        self.assertEqual(self.fetcher.calls,0)

    def test_refresh_required_denied(self):
        self.registry.register_trusted(**dict(self.metadata,state='refresh_required'))
        with self.assertRaises(PermissionError):
            self.gate.import_page(**self.args)

    def test_bad_secret_denied_before_fetch(self):
        self.registry.register_trusted(**self.metadata)
        with self.assertRaises(PermissionError):
            self.gate.import_page(**dict(self.args,import_secret='bad'))
        self.assertEqual(self.fetcher.calls,0)

    def test_legacy_write_scope_denied_before_fetch(self):
        self.registry.db.execute("""INSERT INTO provider_connections VALUES
            (?,?,?,?,?,?,?,?)""",
            ('shop','facebook','page','vault/legacy',
             'pages_manage_posts','connected',200,10))
        self.registry.db.commit()
        with self.assertRaises(PermissionError):
            self.gate.import_page(**self.args)
        self.assertEqual(self.fetcher.calls,0)

    def test_revocation_cannot_be_undone_by_metadata_replay(self):
        self.registry.register_trusted(**self.metadata)
        self.registry.register_trusted(**dict(self.metadata,
            state='revoked',now=50))
        with self.assertRaises(ValueError):
            self.registry.register_trusted(**dict(self.metadata,
                state='connected',now=60))
        with self.assertRaises(PermissionError):
            self.gate.preview_import(**self.args)
        self.assertEqual(self.fetcher.calls,0)

    def test_cross_tenant_denied(self):
        self.registry.register_trusted(**self.metadata)
        with self.assertRaises(PermissionError):
            self.gate.import_page(**dict(self.args,tenant_id='other'))
        self.assertEqual(self.fetcher.calls,0)

if __name__=='__main__':unittest.main()
