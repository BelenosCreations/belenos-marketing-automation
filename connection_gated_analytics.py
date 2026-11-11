"""Fail-closed offline gate for read-only analytics imports.

Checks connection metadata before the provider fetcher is invoked.
This is not OAuth or proof of provider ownership.
"""
class ConnectionGatedAnalyticsAdapter:
    def __init__(self, *, adapter, registry):
        self.adapter=adapter
        self.registry=registry

    def _authorize(self, *, tenant_id, platform, account_id, import_secret, now):
        # Authenticate caller first, before exposing connection status.
        self.adapter.coordinator.importer.authorize(
            tenant_id=tenant_id,platform=platform,
            account_id=account_id,import_secret=import_secret)
        if self.adapter.account_bindings.get((tenant_id,platform))!=account_id:
            raise PermissionError('Provider account not bound to business')
        status=self.registry.status(tenant_id=tenant_id,platform=platform,
                                    account_id=account_id,now=now)
        if status['status']!='connected':
            raise PermissionError('Analytics connection not active')
        return status

    def preview_import(self, *, tenant_id, platform, account_id, import_secret, now):
        self._authorize(tenant_id=tenant_id,platform=platform,
                        account_id=account_id,import_secret=import_secret,now=now)
        return self.adapter.preview_import(
            tenant_id=tenant_id,platform=platform,account_id=account_id,
            import_secret=import_secret,now=now)

    def import_page(self, *, tenant_id, platform, account_id, import_secret, now):
        self._authorize(tenant_id=tenant_id,platform=platform,
                        account_id=account_id,import_secret=import_secret,now=now)
        # The existing adapter delegates to an atomic SQLite import.
        return self.adapter.import_page(
            tenant_id=tenant_id,platform=platform,account_id=account_id,
            import_secret=import_secret,now=now)
