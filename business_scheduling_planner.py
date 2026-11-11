"""Authenticated planning facade: saved business settings -> proposed posting time.

No background task, publication, or approval mutation is performed.
"""
from posting_schedule_policy import SchedulingPlanner

class BusinessSchedulingPlanner:
    def __init__(self, *, settings_service, planner=None):
        self.settings_service=settings_service
        self.planner=planner or SchedulingPlanner()

    def propose(self, *, token, tenant_id, post, start_utc,
                override_local=None, engagement_by_hour=None, now=None):
        record=self.settings_service.get(token=token,tenant_id=tenant_id,now=now)
        if record is None:
            return {'status':'not_configured','scheduled_at':None,
                    'reason':'Configure Manual or Smart scheduling for this business'}
        proposal=self.planner.suggest(
            prefs=record['preferences'],post=post,start_utc=start_utc,
            override_local=override_local,engagement_by_hour=engagement_by_hour)
        return {**proposal,'mode':record['preferences'].mode,
                'settings_revision':record['revision'],
                'business_id':tenant_id,'publishing_enabled':False}
