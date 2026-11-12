"""Live-session-bound scheduling preferences for CI-only PostgreSQL.

This stores *planning preferences*, not scheduled jobs or publication
permission. All SQL is parameterized; a synthetic disposable connection is
required to execute it. No HTTPS gateway, provider or background worker.
"""
import hashlib
import json
import re
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError

from posting_schedule_policy import SchedulePreferences

_SESSION=re.compile(r"[A-Za-z0-9_-]{40,256}\Z")
_TENANT=re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
_CLOCK=re.compile(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]\Z")
_EDITORS="('owner','marketing_manager','content_creator')"
_READ_ROLES="('owner','marketing_manager','content_creator','employee','viewer')"

_READ="""SELECT p.mode,p.timezone_name,p.weekly_json,
                p.preferred_hours_json,p.revision
    FROM scheduling_settings p
    WHERE p.tenant_id=%s
      AND EXISTS (
        SELECT 1 FROM sessions s
        JOIN members m ON m.tenant_id=s.tenant_id
             AND m.subject_id=s.subject_id
        JOIN bam_identities i ON i.subject_id=s.subject_id
        WHERE s.token_hash=%s AND s.tenant_id=p.tenant_id
          AND s.revoked_at IS NULL AND s.expires_at>%s
          AND m.active=1 AND m.role=s.role
          AND i.active=1 AND i.email_verified=1
          AND m.role IN ('owner','marketing_manager','content_creator',
                         'employee','viewer')
      )"""

_CREATE="""INSERT INTO scheduling_settings
    (tenant_id,mode,timezone_name,weekly_json,preferred_hours_json,revision)
    SELECT %s,%s,%s,%s,%s,1
    FROM sessions s
    JOIN members m ON m.tenant_id=s.tenant_id
         AND m.subject_id=s.subject_id
    JOIN bam_identities i ON i.subject_id=s.subject_id
    WHERE s.token_hash=%s AND s.tenant_id=%s
      AND s.revoked_at IS NULL AND s.expires_at>%s
      AND m.active=1 AND m.role=s.role
      AND i.active=1 AND i.email_verified=1
      AND m.role IN ('owner','marketing_manager','content_creator')
    ON CONFLICT(tenant_id) DO NOTHING
    RETURNING revision"""

_UPDATE="""UPDATE scheduling_settings AS p
    SET mode=%s,timezone_name=%s,weekly_json=%s,
        preferred_hours_json=%s,revision=p.revision+1
    WHERE p.tenant_id=%s AND p.revision=%s
      AND EXISTS (
        SELECT 1 FROM sessions s
        JOIN members m ON m.tenant_id=s.tenant_id
             AND m.subject_id=s.subject_id
        JOIN bam_identities i ON i.subject_id=s.subject_id
        WHERE s.token_hash=%s AND s.tenant_id=p.tenant_id
          AND s.revoked_at IS NULL AND s.expires_at>%s
          AND m.active=1 AND m.role=s.role
          AND i.active=1 AND i.email_verified=1
          AND m.role IN ('owner','marketing_manager','content_creator')
      )
    RETURNING revision"""


def _session_context(raw_session_token,tenant_id,server_now):
    if (type(raw_session_token) is not str
            or _SESSION.fullmatch(raw_session_token) is None
            or type(tenant_id) is not str
            or _TENANT.fullmatch(tenant_id) is None
            or type(server_now) is not int
            or not 0<=server_now<2**63):
        raise ValueError("Current business session required")
    return hashlib.sha256(raw_session_token.encode("ascii")).hexdigest()


def _normalized(preferences):
    if type(preferences) is not SchedulePreferences:
        raise ValueError("Validated scheduling preferences required")
    mode=preferences.mode
    zone=preferences.timezone_name
    if (type(mode) is not str or mode not in ("manual","smart")
            or type(zone) is not str or not 1<=len(zone)<=80
            or any(ord(c)<33 or ord(c)>126 for c in zone)):
        raise ValueError("Valid scheduling mode and IANA timezone required")
    try:
        ZoneInfo(zone)
    except (ZoneInfoNotFoundError,ValueError,KeyError) as exc:
        raise ValueError("Unknown IANA timezone") from exc
    weekly=preferences.manual_weekly
    if type(weekly) is not dict or len(weekly)>7:
        raise ValueError("Bounded weekly schedule required")
    clean={}
    total=0
    for day,times in weekly.items():
        if (type(day) is not int or not 0<=day<=6
                or type(times) not in (list,tuple) or len(times)>24
                or any(type(t) is not str or _CLOCK.fullmatch(t) is None
                       for t in times)
                or len(set(times))!=len(times)):
            raise ValueError("Valid unique weekly HH:MM times required")
        clean[str(day)]=sorted(times)
        total+=len(times)
    if mode=="manual" and total==0:
        raise ValueError("Manual planning needs at least one time")
    hours=preferences.preferred_hours
    if (type(hours) not in (tuple,list) or not 1<=len(hours)<=24
            or any(type(h) is not int or not 0<=h<=23 for h in hours)
            or len(set(hours))!=len(hours)):
        raise ValueError("Distinct preferred hours required")
    return (mode,zone,
            json.dumps(clean,sort_keys=True,separators=(",",":")),
            json.dumps(list(hours),separators=(",",":")))


def prepare_session_schedule_settings_read(*,raw_session_token,tenant_id,
                                           server_now):
    digest=_session_context(raw_session_token,tenant_id,server_now)
    return _READ,(tenant_id,digest,server_now)


def summarize_session_schedule_settings(row,*,tenant_id):
    if row is None:
        return None
    if (type(tenant_id) is not str or _TENANT.fullmatch(tenant_id) is None
            or type(row) not in (tuple,list) or len(row)!=5
            or type(row[2]) is not str or type(row[3]) is not str
            or type(row[4]) is not int or row[4]<1):
        raise ValueError("Unexpected private scheduling preference data")
    try:
        weekly=json.loads(row[2])
        hours=json.loads(row[3])
        if type(weekly) is not dict:
            raise ValueError("Invalid weekly data")
        if any(type(k) is not str or not k.isascii() or
               not k.isdecimal() or k.startswith("0") and k!="0"
               for k in weekly):
            raise ValueError("Invalid weekday key")
        converted={int(k):v for k,v in weekly.items()}
        prefs=SchedulePreferences(
            mode=row[0],timezone_name=row[1],manual_weekly=converted,
            preferred_hours=tuple(hours))
        _normalized(prefs)
    except (ValueError,TypeError,KeyError,ZoneInfoNotFoundError,OverflowError,
            AttributeError) as exc:
        raise ValueError("Invalid persisted scheduling preferences") from exc
    return {"tenant_id":tenant_id,"preferences":prefs,"revision":row[4],
            "configured":True,"publishing_enabled":False,
            "posts_scheduled":0}


def prepare_session_schedule_settings_save(*,raw_session_token,tenant_id,
                                           preferences,expected_revision,
                                           server_now):
    digest=_session_context(raw_session_token,tenant_id,server_now)
    if (type(expected_revision) is not int
            or not 0<=expected_revision<2**31-1):
        raise ValueError("Current scheduling revision required")
    mode,zone,weekly_json,hours_json=_normalized(preferences)
    if expected_revision==0:
        return _CREATE,(tenant_id,mode,zone,weekly_json,hours_json,
                        digest,tenant_id,server_now)
    return _UPDATE,(mode,zone,weekly_json,hours_json,tenant_id,
                    expected_revision,digest,server_now)


def summarize_session_schedule_settings_save(row,*,tenant_id,
                                             expected_revision):
    if row is None:
        raise PermissionError("Current editor or settings revision required")
    if (type(row) not in (tuple,list) or len(row)!=1
            or type(row[0]) is not int
            or row[0]!=expected_revision+1):
        raise ValueError("Unexpected scheduling settings revision")
    return {"tenant_id":tenant_id,"revision":row[0],
            "status":"planning_preferences_only",
            "publishing_enabled":False,"posts_scheduled":0}
