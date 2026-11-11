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

    def test_invalid_vault_reference_rejected(self):
        with self.assertRaises(ValueError):
            self.register(vault_reference='secret value with spaces')

    def test_status_excludes_secret_reference(self):
        self.register()
        self.assertNotIn('vault_reference',self.status())
        self.assertFalse(self.status()['publishing_enabled'])

if __name__=='__main__':unittest.main()
