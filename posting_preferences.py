"""Tenant-scoped posting-time preferences; never schedules or publishes.

Owner-only mutation. Smart mode does not invent optimal times; a separate
verified analytics-based optimizer will be required for recommendations.
"""
import json
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from access_policy import Role

class PostingPreferences:
    def __init__(self,*,db,sessions,directory):
        self.db=db
        self.sessions=sessions
        self.directory=directory
        db.execute("""CREATE TABLE IF NOT EXISTS bam_posting_preferences (
            tenant_id TEXT PRIMARY KEY, mode TEXT NOT NULL,
            timezone TEXT NOT NULL, manual_times TEXT NOT NULL,
            updated_at INTEGER NOT NULL, updated_by TEXT NOT NULL)""")
        db.commit()

    def _session(self,*,token,now,tenant_id,owner_only):
        if type(now) is not int or now<0:
            raise ValueError('Server time required')
        session=self.sessions.resolve_current(token,directory=self.directory,now=now)
        if session is None or session.principal.tenant_id!=tenant_id:
            raise PermissionError('Active business session required')
        if owner_only and session.principal.role!=Role.OWNER:
            raise PermissionError('Business owner required')
        return session

    def get(self,*,token,tenant_id,now):
        self._session(token=token,tenant_id=tenant_id,now=now,owner_only=False)
        row=self.db.execute("""SELECT mode,timezone,manual_times
            FROM bam_posting_preferences WHERE tenant_id=?""",(tenant_id,)).fetchone()
        if row is None:
            return {'tenant_id':tenant_id,'mode':'smart','timezone':None,
                    'manual_times':[],'configured':False,
                    'publishing_enabled':False}
        return {'tenant_id':tenant_id,'mode':row[0],'timezone':row[1],
                'manual_times':json.loads(row[2]),'configured':True,
                'publishing_enabled':False}

    def set(self,*,token,tenant_id,mode,timezone,manual_times,now):
        session=self._session(token=token,tenant_id=tenant_id,now=now,owner_only=True)
        if not isinstance(mode,str) or mode not in ('smart','manual'):
            raise ValueError('Invalid scheduling preference')
        if not isinstance(timezone,str) or not timezone.strip() or len(timezone)>80:
            raise ValueError('IANA timezone required')
        try:
            ZoneInfo(timezone)
        except (ZoneInfoNotFoundError,ValueError,KeyError) as exc:
            raise ValueError('Unknown IANA timezone') from exc
        if (type(manual_times) is not list or len(manual_times)>24
                or any(not isinstance(value,str) or len(value)!=5
                       or re.fullmatch(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]',value) is None
                       for value in manual_times)
                or len(set(manual_times))!=len(manual_times)):
            raise ValueError('Invalid or duplicate manual times')
        if mode=='manual' and not manual_times:
            raise ValueError('Manual mode requires at least one time')
        if mode=='smart' and manual_times:
            raise ValueError('Smart mode cannot include manual times')
        times=sorted(manual_times)
        with self.db:
            self.db.execute("""INSERT INTO bam_posting_preferences
                (tenant_id,mode,timezone,manual_times,updated_at,updated_by)
                VALUES (?,?,?,?,?,?)
                ON CONFLICT(tenant_id) DO UPDATE SET
                mode=excluded.mode,timezone=excluded.timezone,
                manual_times=excluded.manual_times,updated_at=excluded.updated_at,
                updated_by=excluded.updated_by""",
                (tenant_id,mode,timezone,json.dumps(times),now,
                 session.principal.subject_id))
        return self.get(token=token,tenant_id=tenant_id,now=now)
