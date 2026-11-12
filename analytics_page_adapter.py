"""Provider-neutral, offline analytics page adapter.

Only accepts pages from a server-injected trusted fetcher. No HTTP, OAuth,
provider verification or background execution is implemented.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

class AnalyticsPageAdapter:
    def __init__(self, *, coordinator, fetcher, account_bindings, timezone_by_tenant):
        self.coordinator=coordinator
        self.fetcher=fetcher
        self.account_bindings=dict(account_bindings)
        self.timezone_by_tenant=dict(timezone_by_tenant)

    def preview_import(self, *, tenant_id, platform, account_id,
                       import_secret, now):
        # Authenticate before invoking a fetcher or reading any checkpoint.
        self.coordinator.importer.authorize(
            tenant_id=tenant_id,platform=platform,account_id=account_id,
            import_secret=import_secret)
        if self.account_bindings.get((tenant_id,platform))!=account_id:
            raise PermissionError('Provider account not bound to business')
        if type(now) is not int or now<0:
            raise ValueError('Invalid time')
        zone_name=self.timezone_by_tenant.get(tenant_id)
        try:
            zone=ZoneInfo(zone_name)
        except (TypeError,ValueError,ZoneInfoNotFoundError) as exc:
            raise ValueError('Business timezone unavailable') from exc
        previous=self.coordinator.checkpoint(
            tenant_id=tenant_id,platform=platform,account_id=account_id)
        cursor=None if previous is None else previous['cursor']
        page=self.fetcher.fetch_page(tenant_id=tenant_id,platform=platform,
                                    account_id=account_id,cursor=cursor)
        if not isinstance(page,dict) or set(page)!={'next_cursor','posts'}:
            raise ValueError('Malformed provider page')
        posts=page['posts']
        if not isinstance(posts,(list,tuple)) or not 1<=len(posts)<=100:
            raise ValueError('Provider page must have 1 to 100 posts')
        next_cursor=page['next_cursor']
        if not isinstance(next_cursor,str) or not next_cursor or len(next_cursor)>512:
            raise ValueError('Invalid next cursor')
        observations=[]
        for post in posts:
            if not isinstance(post,dict) or set(post)!={
                    'post_id','published_at','engagement_count','impression_count'}:
                raise ValueError('Malformed provider post')
            published=post['published_at']
            if type(published) is not int or published<0 or published>now:
                raise ValueError('Invalid publication timestamp')
            local=datetime.fromtimestamp(published,timezone.utc).astimezone(zone)
            # Weekly hour bucket is stable across DST and comparable within
            # one platform; actual posting date remains in the observation.
            candidate=f'{local.weekday()}:{local.hour:02d}'
            observations.append(dict(source_post_id=post['post_id'],
                candidate=candidate,engagement_count=post['engagement_count'],
                impression_count=post['impression_count'],measured_at=now))
        return {'expected_cursor':cursor,'next_cursor':next_cursor,
                'observations':observations,'status':'preview',
                'publishing_enabled':False}

    def import_page(self, *, tenant_id, platform, account_id,
                    import_secret, now, admission_guard=None):
        preview=self.preview_import(
            tenant_id=tenant_id,platform=platform,account_id=account_id,
            import_secret=import_secret,now=now)
        return self.coordinator.apply_batch(
            tenant_id=tenant_id,platform=platform,account_id=account_id,
            import_secret=import_secret,now=now,
            expected_cursor=preview['expected_cursor'],
            next_cursor=preview['next_cursor'],
            observations=preview['observations'],
            admission_guard=admission_guard)
