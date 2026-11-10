"""Offline manual/smart schedule preview. No job creation or publishing."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from schedule_readiness import assess_schedule_readiness

def preview_schedule(*, ledger, token, tenant_id, intent_id, mode,
                     timezone_name, manual_local=None, smart_candidates=None,
                     now=None):
    if mode not in ('manual','smart'):
        raise ValueError('Unknown scheduling mode')
    try:
        zone=ZoneInfo(timezone_name)
    except (TypeError, ValueError, ZoneInfoNotFoundError) as exc:
        raise ValueError('Invalid timezone') from exc
    if mode=='manual':
        if not isinstance(manual_local,str) or smart_candidates is not None:
            raise ValueError('Manual mode requires only manual_local')
        candidates=[manual_local]
    else:
        if manual_local is not None or not isinstance(smart_candidates,(list,tuple)):
            raise ValueError('Smart mode requires candidates only')
        if not 1<=len(smart_candidates)<=20:
            raise ValueError('Smart mode requires 1 to 20 candidates')
        candidates=smart_candidates
    instants=[]
    for local in candidates:
        if not isinstance(local,str):
            raise ValueError('Local times must be strings')
        try:
            parsed=datetime.strptime(local,'%Y-%m-%dT%H:%M')
        except ValueError as exc:
            raise ValueError('Local time must be YYYY-MM-DDTHH:MM') from exc
        possible=[]
        for fold in (0,1):
            aware=parsed.replace(tzinfo=zone,fold=fold)
            utc=aware.astimezone(timezone.utc)
            if utc.astimezone(zone).replace(tzinfo=None)==parsed:
                possible.append(int(utc.timestamp()))
        if len(set(possible))!=1:
            raise ValueError('Ambiguous or nonexistent local time')
        instants.append(possible[0])
    if len(set(instants))!=len(instants):
        raise ValueError('Duplicate scheduling candidates')
    selected=min(instants)
    assessment=assess_schedule_readiness(
        ledger=ledger,token=token,tenant_id=tenant_id,
        intent_id=intent_id,proposed_at=selected,now=now)
    return {'mode':mode,'timezone':timezone_name,
            'candidate_count':len(instants),'selected_at':selected,
            'selection_policy':'earliest_candidate_only',
            'readiness':assessment,'status':'held',
            'scheduled_job_created':False,'publishing_enabled':False}
