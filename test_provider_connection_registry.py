import sqlite3
import unittest
from provider_connection_registry import ProviderConnectionRegistry

class ProviderConnectionRegistryTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.registry=ProviderConnectionRegistry(self.db)
        self.params=dict(tenant_id='shop',platform='facebook',
            account_id='page1',vault_reference='vault/analytics/shop/page1',
            scope='read_insights',state='connected',expires_at=200,now=100)

    def register(self,**changes):
        values=dict(self.params)
        values.update(changes)
        return self.registry.register_trusted(**values)

    def status(self,**changes):
        args=dict(tenant_id='shop',platform='facebook',
                  account_id='page1',now=100)
        args.update(changes)
        return self.registry.status(**args)

    def test_missing_connection(self):
        self.assertEqual(self.status()['status'],'not_connected')

    def test_connected_status(self):
        self.register()
        self.assertEqual(self.status()['status'],'connected')

    def test_expired_connection(self):
        self.register()
        self.assertEqual(self.status(now=201)['status'],'expired')

    def test_revocation_state(self):
        self.register(state='revoked')
        self.assertEqual(self.status()['status'],'revoked')

    def test_business_isolation(self):
        self.register()
        self.assertEqual(self.status(tenant_id='other')['status'],'not_connected')

    def test_platform_isolation(self):
        self.register()
        self.assertEqual(self.status(platform='instagram')['status'],'not_connected')

    def test_publish_scope_rejected(self):
        with self.assertRaises(ValueError):
            self.register(scope='pages_publish')

    def test_scope_allowlist_blocks_write_capabilities_and_ambiguous_text(self):
        for dangerous in ('pages_publish','pages_manage_posts','ads_management',
                          'instagram_content_publish','READ_INSIGHTS',
                          'read_insights pages_manage_posts',''):
            with self.subTest(scope=dangerous):
                with self.assertRaises(ValueError):
                    self.register(scope=dangerous)
        self.assertEqual(self.status()['status'],'not_connected')

    def test_stale_updates_cannot_restore_or_override_newer_state(self):
        self.register(now=100)
        self.register(state='refresh_required',now=150)
        for stale_state in ('connected','pending','revoked'):
            with self.subTest(state=stale_state):
                with self.assertRaises(ValueError):
                    self.register(state=stale_state,now=120)
        self.assertEqual(self.status(now=151)['status'],'refresh_required')
        self.register(state='revoked',now=200)
        for attempted_state in ('connected','pending','refresh_required','revoked'):
            with self.subTest(state=attempted_state):
                with self.assertRaises(ValueError):
                    self.register(state=attempted_state,now=201)
        self.assertEqual(self.status(now=202)['status'],'revoked')
        self.assertFalse(self.status(now=202)['publishing_enabled'])

    def test_equal_timestamp_replay_is_rejected(self):
        self.register(now=100)
        with self.assertRaises(ValueError):
            self.register(now=100,state='revoked',vault_reference='vault/other')
        self.assertEqual(self.status(now=100)['status'],'connected')

    def test_unapproved_legacy_scope_is_not_connected(self):
        self.db.execute("""INSERT INTO provider_connections VALUES
            (?,?,?,?,?,?,?,?)""",
            ('shop','facebook','page1','vault/legacy',
             'pages_manage_posts','connected',200,100))
        self.db.commit()
        result=self.status(now=101)
        self.assertEqual(result['status'],'refresh_required')
        self.assertFalse(result['publishing_enabled'])
        self.assertNotIn('vault_reference',result)

    def test_future_dated_metadata_is_untrusted(self):
        self.register(now=100)
        self.assertEqual(self.status(now=99)['status'],'refresh_required')

    def test_invalid_vault_reference_rejected(self):
        with self.assertRaises(ValueError):
            self.register(vault_reference='secret value with spaces')

    def test_status_excludes_secret_reference(self):
        self.register()
        self.assertNotIn('vault_reference',self.status())
        self.assertFalse(self.status()['publishing_enabled'])

if __name__=='__main__':unittest.main()
