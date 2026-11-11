"""Read-only analytics synchronization health and recovery recommendations.

No retries, network calls, credential exposure or publication.
"""
def assess_sync_health(*, coordinator, importer, tenant_id, platform,
                       account_id, import_secret, now,
                       max_checkpoint_age=86400):
    importer.authorize(tenant_id=tenant_id,platform=platform,
                       account_id=account_id,import_secret=import_secret)
    if (type(now) is not int or now<0 or type(max_checkpoint_age) is not int
            or not 1<=max_checkpoint_age<=2592000):
        raise ValueError('Invalid health assessment window')
    checkpoint=coordinator.checkpoint(tenant_id=tenant_id,platform=platform,
                                      account_id=account_id)
    if checkpoint is None:
        return {'status':'not_started','last_sync_at':None,
                'age_seconds':None,'action':'initial_read_only_import',
                'publishing_enabled':False}
    updated=checkpoint['updated_at']
    if type(updated) is not int or updated<0 or updated>now:
        return {'status':'invalid_checkpoint','last_sync_at':None,
                'age_seconds':None,'action':'manual_investigation',
                'publishing_enabled':False}
    age=now-updated
    return {'status':'stale' if age>max_checkpoint_age else 'current',
            'last_sync_at':updated,'age_seconds':age,
            'action':'review_provider_connection' if age>max_checkpoint_age
                     else 'none','publishing_enabled':False}
