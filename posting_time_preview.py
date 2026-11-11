"""Read-only preview of saved BAM posting-time preferences.

Manual preferences yield possible future local clock slots only; no queued
posts or approval. Ambiguous/nonexistent DST wall times are omitted.
Smart mode never pretends to know engagement-based optimal times.
"""
from datetime import datetime, timedelta, timezone, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import re

_CLOCK = re.compile(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]\Z')

def build_posting_time_preview(preferences, *, server_now, days=7, max_slots=30):
    if (type(preferences) is not dict
            or type(server_now) is not int or server_now < 0
            or type(days) is not int or not 1 <= days <= 14
            or type(max_slots) is not int or not 1 <= max_slots <= 100):
        raise ValueError('Trusted posting preview inputs required')
    expected = {'tenant_id', 'mode', 'timezone', 'manual_times',
                'configured', 'publishing_enabled'}
    if (set(preferences) != expected
            or type(preferences['tenant_id']) is not str
            or not preferences['tenant_id'].strip()
            or len(preferences['tenant_id']) > 128
            or preferences['publishing_enabled'] is not False
            or type(preferences['configured']) is not bool
            or preferences['mode'] not in ('manual', 'smart')
            or type(preferences['manual_times']) is not list
            or len(preferences['manual_times']) > 24):
        raise ValueError('Invalid saved business preferences')
    tenant=preferences['tenant_id']
    configured=preferences['configured']
    zone_name=preferences['timezone']
    times=preferences['manual_times']
    if not configured:
        if preferences['mode'] != 'smart' or zone_name is not None or times:
            raise ValueError('Inconsistent unconfigured preferences')
        return {'tenant_id':tenant,'mode':'smart','timezone':None,
                'status':'not_configured','slots':[],'skipped_dst':0,
                'truncated':False,'publishing_enabled':False}
    if (type(zone_name) is not str or not zone_name.strip()
            or zone_name != zone_name.strip() or len(zone_name)>80):
        raise ValueError('Valid saved timezone required')
    try:
        zone=ZoneInfo(zone_name)
    except (ZoneInfoNotFoundError,ValueError,KeyError) as exc:
        raise ValueError('Unsupported saved timezone') from exc
    if (any(type(value) is not str or _CLOCK.fullmatch(value) is None
            for value in times) or len(times)!=len(set(times))
            or (preferences['mode']=='manual' and not times)
            or (preferences['mode']=='smart' and times)):
        raise ValueError('Invalid saved manual times')
    if preferences['mode']=='smart':
        return {'tenant_id':tenant,'mode':'smart','timezone':zone_name,
                'status':'needs_audience_data','slots':[],'skipped_dst':0,
                'truncated':False,'publishing_enabled':False}
    now=datetime.fromtimestamp(server_now,tz=timezone.utc)
    first=now.astimezone(zone).date()
    candidates=[]
    skipped_dst=0
    for offset in range(days):
        local_date=first+timedelta(days=offset)
        for clock in sorted(times):
            hour,minute=(int(v) for v in clock.split(':'))
            wall=datetime.combine(local_date,time(hour,minute))
            possible=set()
            for fold in (0,1):
                aware=wall.replace(tzinfo=zone,fold=fold)
                instant=aware.astimezone(timezone.utc)
                if instant.astimezone(zone).replace(tzinfo=None)==wall:
                    possible.add(instant)
            if len(possible)!=1:
                # DST gap or fall-back ambiguity: never silently choose a fold.
                skipped_dst+=1
                continue
            instant=next(iter(possible))
            if instant<=now:
                continue
            candidates.append((instant,local_date.isoformat(),clock))
    candidates.sort(key=lambda item:item[0])
    slots=[{'local_date':day,'local_time':clock,
            'utc_at':instant.isoformat(timespec='seconds')}
           for instant,day,clock in candidates[:max_slots]]
    return {'tenant_id':tenant,'mode':'manual','timezone':zone_name,
            'status':'manual_preview','slots':slots,
            'skipped_dst':skipped_dst,'truncated':len(candidates)>max_slots,
            'publishing_enabled':False}
