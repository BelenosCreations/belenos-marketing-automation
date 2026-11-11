"""Business-scoped *proposed* content calendar, never a publishing queue.

Saving a proposal records a possible owner-configured manual clock slot for
an existing held content request. No job scheduler, social provider, media
approval or auto-publishing service is permitted to execute these records.
"""
import re
import sqlite3

from access_policy import Action, Resource, require_permission
from posting_time_preview import build_posting_time_preview

_ID=re.compile(r'[a-f0-9]{32}\Z')
_UTC=re.compile(r'\d{4}-\d\d-\d\dT(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d\+00:00\Z')

class CalendarProposals:
    def __init__(self, *, db, sessions, directory,
                 content_service, preferences):
        self.db=db
        self.sessions=sessions
        self.directory=directory
        self.content_service=content_service
        self.preferences=preferences
        db.execute("""CREATE TABLE IF NOT EXISTS bam_calendar_proposals(
            tenant_id TEXT NOT NULL,
            request_id TEXT NOT NULL,
            draft_revision INTEGER NOT NULL,
            utc_at TEXT NOT NULL,
            local_date TEXT NOT NULL,
            local_time TEXT NOT NULL,
            timezone TEXT NOT NULL,
            updated_at INTEGER NOT NULL,
            updated_by TEXT NOT NULL,
            PRIMARY KEY(tenant_id,request_id),
            UNIQUE(tenant_id,utc_at))""")
        db.commit()

    def _authorize(self,*,token,now,action):
        if type(now) is not int or now<0:
            raise ValueError('Trusted server clock required')
        session=self.sessions.resolve_current(
            token,directory=self.directory,now=now)
        if session is None:
            raise PermissionError('Active BAM session required')
        member=session.principal
        require_permission(member,action,Resource(member.tenant_id))
        return member

    def _preview(self,*,token,tenant,now):
        prefs=self.preferences.get(token=token,tenant_id=tenant,now=now)
        return build_posting_time_preview(
            prefs,server_now=now,days=14,max_slots=100)

    def list_mine_business(self,*,token,now):
        principal=self._authorize(token=token,now=now,
                                   action=Action.READ_DRAFTS)
        tenant=principal.tenant_id
        rows=self.db.execute("""SELECT request_id,draft_revision,utc_at,
            local_date,local_time,timezone
            FROM bam_calendar_proposals WHERE tenant_id=?
            ORDER BY utc_at ASC LIMIT 201""",(tenant,)).fetchall()
        if len(rows)>200:
            raise ValueError('Calendar proposal list too large')
        preview=self._preview(token=token,tenant=tenant,now=now)
        permitted={row['utc_at'] for row in preview['slots']}
        items=[]
        for request_id,revision,utc_at,day,clock,zone in rows:
            draft=self.content_service.get(
                token=token,tenant_id=tenant,request_id=request_id,now=now)
            current_revision=draft['revision'] if draft else None
            content_changed=(draft is None or
                current_revision!=revision or
                draft['status'] not in ('needs_content','ready_for_review'))
            slot_current=(preview['status']=='manual_preview' and
                          zone==preview['timezone'] and utc_at in permitted)
            items.append({
                'request_id':request_id,'draft_revision':revision,
                'current_revision':current_revision,
                'utc_at':utc_at,'local_date':day,'local_time':clock,
                'timezone':zone,
                'content_changed':content_changed,
                'slot_current':slot_current,
                'publishing_enabled':False
            })
        return {'tenant_id':tenant,'status':'proposal_only',
                'items':items,'posts_scheduled':0,
                'publishing_enabled':False}

    def propose(self,*,token,now,request_id,expected_revision,utc_at):
        principal=self._authorize(token=token,now=now,
                                   action=Action.EDIT_DRAFT)
        if (type(request_id) is not str or _ID.fullmatch(request_id) is None
                or type(expected_revision) is not int or expected_revision<1
                or type(utc_at) is not str or _UTC.fullmatch(utc_at) is None):
            raise ValueError('Validated held draft and future slot required')
        tenant=principal.tenant_id
        draft=self.content_service.get(
            token=token,tenant_id=tenant,request_id=request_id,now=now)
        if draft is None:
            raise KeyError('Content request not found')
        if draft['revision']!=expected_revision:
            raise ValueError('Draft changed; refresh before proposing')
        if draft['status'] not in ('needs_content','ready_for_review'):
            raise ValueError('Held draft is not eligible for a proposed slot')
        preview=self._preview(token=token,tenant=tenant,now=now)
        if preview['status']!='manual_preview':
            raise ValueError('Manual owner-configured posting times required')
        slot=next((value for value in preview['slots']
                   if value['utc_at']==utc_at),None)
        if slot is None:
            raise ValueError('Choose an unambiguous upcoming configured slot')
        # Record the exact draft revision so later edits invalidate the
        # proposal. SQLite UNIQUE(tenant_id,utc_at) prevents double-booking.
        try:
            with self.db:
                current=self.content_service.requests.get(
                    tenant_id=tenant,request_id=request_id)
                if current is None or current['revision']!=expected_revision:
                    raise ValueError('Draft changed; refresh before proposing')
                self.db.execute("""INSERT INTO bam_calendar_proposals
                   (tenant_id,request_id,draft_revision,utc_at,
                    local_date,local_time,timezone,updated_at,updated_by)
                   VALUES (?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(tenant_id,request_id) DO UPDATE SET
                    draft_revision=excluded.draft_revision,
                    utc_at=excluded.utc_at,
                    local_date=excluded.local_date,
                    local_time=excluded.local_time,
                    timezone=excluded.timezone,
                    updated_at=excluded.updated_at,
                    updated_by=excluded.updated_by""",
                    (tenant,request_id,expected_revision,utc_at,
                     slot['local_date'],slot['local_time'],
                     preview['timezone'],now,principal.subject_id))
        except sqlite3.IntegrityError as exc:
            raise ValueError('Proposed time already used by this business') from exc
        return {'tenant_id':tenant,'request_id':request_id,
                'utc_at':utc_at,'status':'proposal_only',
                'posts_scheduled':0,'publishing_enabled':False}

    def discard(self,*,token,now,request_id):
        principal=self._authorize(token=token,now=now,
                                   action=Action.EDIT_DRAFT)
        if type(request_id) is not str or _ID.fullmatch(request_id) is None:
            raise ValueError('Validated draft request required')
        with self.db:
            deleted=self.db.execute("""DELETE FROM bam_calendar_proposals
                WHERE tenant_id=? AND request_id=?""",
                (principal.tenant_id,request_id))
        return {'tenant_id':principal.tenant_id,
                'request_id':request_id,'removed':deleted.rowcount,
                'status':'proposal_only','posts_scheduled':0,
                'publishing_enabled':False}
