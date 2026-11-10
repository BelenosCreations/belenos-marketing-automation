"""BAM offline posting-time policy and explainable smart scheduling.

Pure planning only. No background jobs, external analytics or publishing.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

@dataclass(frozen=True)
class SchedulePreferences:
    mode: str
    timezone_name: str
    manual_weekly: dict
    preferred_hours: tuple = (9,12,17,19)

    def __post_init__(self):
        if self.mode not in ('manual','smart'):
            raise ValueError('Unknown scheduling mode')
        ZoneInfo(self.timezone_name)
        if not isinstance(self.manual_weekly,dict):
            raise ValueError('Manual weekly times must be a dictionary')
        for weekday, times in self.manual_weekly.items():
            if type(weekday) is not int or weekday not in range(7):
                raise ValueError('Weekdays must be 0-6')
            if not isinstance(times,(list,tuple)):
                raise ValueError('Times must be a list')
            for value in times:
                if (not isinstance(value,str) or len(value)!=5
                        or value[2]!=':' or not value[:2].isdigit()
                        or not value[3:].isdigit()
                        or int(value[:2])>23 or int(value[3:])>59):
                    raise ValueError('Time must be HH:MM')
        if not self.preferred_hours or any(type(h) is not int or h not in range(24)
                                           for h in self.preferred_hours):
            raise ValueError('Preferred hours must be 0-23')

@dataclass(frozen=True)
class PostContext:
    subject: str
    audience: str
    platform: str
    ready_for_review: bool = False
    approved: bool = False

class SchedulingPlanner:
    @staticmethod
    def _candidates(prefs, start_utc, days):
        tz=ZoneInfo(prefs.timezone_name)
        local=start_utc.astimezone(tz)
        result=[]
        for offset in range(days+1):
            day=(local+timedelta(days=offset)).date()
            for hour in range(24):
                for minute in (0,30):
                    candidate=datetime(day.year,day.month,day.day,hour,minute,tzinfo=tz)
                    # Reject nonexistent DST times and avoid ambiguous fold=1.
                    if candidate.astimezone(timezone.utc).astimezone(tz).replace(fold=0)!=candidate:
                        continue
                    utc=candidate.astimezone(timezone.utc)
                    if utc>start_utc:
                        result.append((candidate,utc))
        return result

    def suggest(self, *, prefs, post, start_utc, override_local=None,
                engagement_by_hour=None, days=14):
        if start_utc.tzinfo is None:
            raise ValueError('start_utc must be timezone-aware')
        if not 1<=days<=60:
            raise ValueError('Invalid planning horizon')
        if not post.ready_for_review or not post.approved:
            return {'status':'held','scheduled_at':None,
                    'reason':'Draft is incomplete or awaiting approval'}
        tz=ZoneInfo(prefs.timezone_name)
        if override_local is not None:
            if override_local.tzinfo is None:
                raise ValueError('Override must include timezone')
            local=override_local.astimezone(tz)
            if local.astimezone(timezone.utc)<=start_utc:
                raise ValueError('Override must be in the future')
            return {'status':'proposed','scheduled_at':local.isoformat(),
                    'reason':'Explicit per-post time override'}
        candidates=self._candidates(prefs,start_utc,days)
        if prefs.mode=='manual':
            allowed={(weekday,time) for weekday,times in prefs.manual_weekly.items()
                     for time in times}
            matched=[(local,utc) for local,utc in candidates
                     if (local.weekday(),local.strftime('%H:%M')) in allowed]
            if not matched:
                return {'status':'no_slot','scheduled_at':None,
                        'reason':'No configured manual slot in planning horizon'}
            local,_=min(matched,key=lambda pair:pair[1])
            return {'status':'proposed','scheduled_at':local.isoformat(),
                    'reason':'Next exact user-configured weekly posting time'}
        # Explainable heuristics are fallback suggestions, not claimed engagement data.
        engagement_by_hour=engagement_by_hour or {}
        if any(type(h) is not int or h not in range(24) or
               not isinstance(score,(int,float)) or isinstance(score,bool)
               for h,score in engagement_by_hour.items()):
            raise ValueError('Invalid engagement observations')
        subject=post.subject.lower()
        audience=post.audience.lower()
        hours=set(prefs.preferred_hours)
        if any(word in subject for word in ('event','tonight','opening','hours')):
            hours.update((8,9,11,16))
        if any(word in audience for word in ('business','office','professional')):
            hours.update((8,12,13,17))
        if any(word in audience for word in ('family','parent','consumer')):
            hours.update((10,18,19,20))
        selected=[pair for pair in candidates if pair[0].hour in hours]
        if not selected:
            return {'status':'no_slot','scheduled_at':None,
                    'reason':'No eligible smart suggestion'}
        def score(pair):
            local,utc=pair
            historical=engagement_by_hour.get(local.hour,0)
            preference=2 if local.hour in prefs.preferred_hours else 0
            # Earlier times break ties; do not invent platform analytics.
            return (historical+preference,-utc.timestamp())
        local,_=max(selected,key=score)
        return {'status':'proposed','scheduled_at':local.isoformat(),
                'reason':'Smart suggestion using audience, subject, local time and supplied engagement observations; no live analytics inferred'}
