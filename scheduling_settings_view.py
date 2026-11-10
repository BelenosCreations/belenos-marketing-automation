"""Scheduling settings presentation model for future Android screens.

Only transforms authenticated service data; no UI framework or publishing.
"""
from posting_schedule_policy import SchedulePreferences

class SchedulingSettingsView:
    def __init__(self, service):
        self.service=service

    def load(self, *, token, tenant_id, now=None):
        record=self.service.get(token=token,tenant_id=tenant_id,now=now)
        if record is None:
            return {'configured':False,'business_id':tenant_id,
                    'available_modes':['manual','smart'],
                    'publishing_enabled':False}
        p=record['preferences']
        return {'configured':True,'business_id':tenant_id,
                'mode':p.mode,'timezone':p.timezone_name,
                'manual_weekly':{str(day):list(times) for day,times in p.manual_weekly.items()},
                'preferred_hours':list(p.preferred_hours),
                'revision':record['revision'],
                'available_modes':['manual','smart'],
                'publishing_enabled':False}

    def save(self, *, token, tenant_id, payload, now=None):
        if not isinstance(payload,dict):
            raise ValueError('Settings payload must be an object')
        required={'mode','timezone','manual_weekly','preferred_hours'}
        if set(payload)!=required|{'expected_revision'} and set(payload)!=required:
            raise ValueError('Unexpected or missing settings fields')
        weekly=payload['manual_weekly']
        if not isinstance(weekly,dict) or any(
                not isinstance(k,str) or not k.isdigit() for k in weekly):
            raise ValueError('Weekday keys must be numeric strings')
        hours=payload['preferred_hours']
        if not isinstance(hours,(list,tuple)):
            raise ValueError('Preferred hours must be an array')
        prefs=SchedulePreferences(mode=payload['mode'],
            timezone_name=payload['timezone'],
            manual_weekly={int(k):v for k,v in weekly.items()},
            preferred_hours=tuple(hours))
        revision=self.service.save(token=token,tenant_id=tenant_id,
            preferences=prefs,expected_revision=payload.get('expected_revision'),
            now=now)
        return {'saved':True,'revision':revision,'publishing_enabled':False}
