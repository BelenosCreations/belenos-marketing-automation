"""Server-side authenticated offline analytics import boundary.

Caller must supply trusted configuration from secret management. This module
does not contact social providers or verify externally supplied metric values.
"""
import hmac
import re

class AnalyticsImportBoundary:
    def __init__(self, *, store, account_bindings, import_secrets):
        self.store=store
        self.account_bindings=dict(account_bindings)
        self.import_secrets=dict(import_secrets)

    def authorize(self, *, tenant_id, platform, account_id, import_secret):
        key=(tenant_id,platform)
        expected_account=self.account_bindings.get(key)
        expected_secret=self.import_secrets.get(key)
        if (not isinstance(expected_account,str)
                or not isinstance(expected_secret,str) or not expected_secret
                or not isinstance(account_id,str) or not isinstance(import_secret,str)
                or not hmac.compare_digest(expected_account,account_id)
                or not hmac.compare_digest(expected_secret,import_secret)):
            raise PermissionError('Authorized analytics import required')

    def import_observation(self, *, tenant_id, platform, account_id,
                           import_secret, source_post_id, candidate,
                           engagement_count, impression_count, measured_at):
        self.authorize(tenant_id=tenant_id,platform=platform,
                       account_id=account_id,import_secret=import_secret)
        if (type(engagement_count) is not int or type(impression_count) is not int
                or engagement_count<0 or impression_count<=0
                or engagement_count>impression_count):
            raise ValueError('Invalid engagement/impression counts')
        if (not isinstance(source_post_id,str)
                or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}',source_post_id)):
            raise ValueError('Invalid source post identifier')
        return self.store.ingest_trusted(
            tenant_id=tenant_id,platform=platform,source_post_id=source_post_id,
            candidate=candidate,engagement_rate=engagement_count/impression_count,
            measured_at=measured_at,source_name='authenticated_offline_import')
