"""Read-only multi-post schedule preview using saved business settings.

Preview does not create jobs, alter drafts, or enable publishing.
"""
from datetime import timedelta

class SchedulingPreview:
    def __init__(self, *, business_planner):
        self.business_planner=business_planner

    def preview(self, *, token, tenant_id, posts, start_utc,
                engagement_by_hour=None, now=None):
        if not isinstance(posts,(list,tuple)) or not 1<=len(posts)<=30:
            raise ValueError('Preview requires 1-30 posts')
        # Authenticate even when every post is held.
        settings=self.business_planner.settings_service.get(
            token=token,tenant_id=tenant_id,now=now)
        if settings is None:
            return {'status':'not_configured','business_id':tenant_id,
                    'items':[],'publishing_enabled':False}
        items=[]
        cursor=start_utc
        for index,post in enumerate(posts):
            result=self.business_planner.planner.suggest(
                prefs=settings['preferences'],post=post,start_utc=cursor,
                engagement_by_hour=engagement_by_hour)
            items.append({'index':index,**result})
            if result['status']=='proposed':
                from datetime import datetime
                candidate=datetime.fromisoformat(result['scheduled_at'])
                # Keep successive proposed posts at least one minute apart.
                cursor=candidate+timedelta(minutes=1)
        return {'status':'preview','business_id':tenant_id,
                'mode':settings['preferences'].mode,
                'settings_revision':settings['revision'],
                'items':items,'publishing_enabled':False,
                'note':'Illustrative suggestions only; no queue or posting'}
