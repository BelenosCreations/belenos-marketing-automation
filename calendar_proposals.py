"""Business-scoped *proposed* content calendar, never a publishing queue.

Saving a proposal records a possible owner-configured manual clock slot for
an existing held content request. No job scheduler, social provider, media
approval or auto-publishing service is permitted to execute these records.
"""
import re
import sqlite3
import uuid

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
            proposal_token TEXT NOT NULL,
            PRIMARY KEY(tenant_id,request_id),
            UNIQUE(tenant_id,utc_at))""")
        # Preserve existing local proposals while introducing an independent
        # write-version token. Unlike second-resolution timestamps, a fresh
        # random token prevents stale update/delete and remove/recreate ABA.
        columns={row[1] for row in
                 db.execute('PRAGMA table_info(bam_calendar_proposals)')}
        if 'proposal_token' not in columns:
            db.execute("ALTER TABLE bam_calendar_proposals "
                       "ADD COLUMN proposal_token TEXT NOT NULL DEFAULT ''")
        for tenant,request_id in db.execute(
                "SELECT tenant_id,request_id FROM bam_calendar_proposals "
                "WHERE proposal_token=''").fetchall():
            db.execute("UPDATE bam_calendar_proposals "
                       "SET proposal_token=? WHERE tenant_id=? AND request_id=? "
                       "AND proposal_token=''",
                       (uuid.uuid4().hex,tenant,request_id))
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
            local_date,local_time,timezone,proposal_token
            FROM bam_calendar_proposals WHERE tenant_id=?
            ORDER BY utc_at ASC LIMIT 201""",(tenant,)).fetchall()
        if len(rows)>200:
            raise ValueError('Calendar proposal list too large')
        preview=self._preview(token=token,tenant=tenant,now=now)
        permitted={row['utc_at'] for row in preview['slots']}
        items=[]
        for request_id,revision,utc_at,day,clock,zone,proposal_token in rows:
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
                'timezone':zone,'proposal_token':proposal_token,
                'content_changed':content_changed,
                'slot_current':slot_current,
                'publishing_enabled':False
            })
        return {'tenant_id':tenant,'status':'proposal_only',
                'items':items,'posts_scheduled':0,
                'publishing_enabled':False}

    def propose(self,*,token,now,request_id,expected_revision,utc_at,
                expected_proposal_token):
        principal=self._authorize(token=token,now=now,
                                   action=Action.EDIT_DRAFT)
        if (type(request_id) is not str or _ID.fullmatch(request_id) is None
                or type(expected_revision) is not int or expected_revision<1
                or type(utc_at) is not str or _UTC.fullmatch(utc_at) is None
                or (expected_proposal_token is not None and
                    (type(expected_proposal_token) is not str or
                     _ID.fullmatch(expected_proposal_token) is None))):
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
        # Enforce the draft revision and proposal version in the same SQL
        # write operation. A prior Python SELECT is not a write lock and can
        # go stale between editors using independent SQLite connections.
        # The proposal remains *non-executable*: zero scheduling or posting.
        proposal_token=uuid.uuid4().hex
        guard="""SELECT 1 FROM content_requests
            WHERE tenant_id=? AND request_id=? AND revision=?
            AND status IN ('needs_content','ready_for_review')"""
        try:
            with self.db:
                if expected_proposal_token is None:
                    changed=self.db.execute("""INSERT INTO bam_calendar_proposals
                        (tenant_id,request_id,draft_revision,utc_at,
                         local_date,local_time,timezone,updated_at,updated_by,
                         proposal_token)
                        SELECT ?,?,?,?,?,?,?,?,?,?
                        WHERE EXISTS ("""+guard+""")
                        ON CONFLICT(tenant_id,request_id) DO NOTHING""",
                        (tenant,request_id,expected_revision,utc_at,
                         slot['local_date'],slot['local_time'],
                         preview['timezone'],now,principal.subject_id,
                         proposal_token,tenant,request_id,expected_revision))
                else:
                    changed=self.db.execute("""UPDATE bam_calendar_proposals
                        SET draft_revision=?,utc_at=?,local_date=?,
                            local_time=?,timezone=?,updated_at=?,
                            updated_by=?,proposal_token=?
                        WHERE tenant_id=? AND request_id=? AND proposal_token=?
                        AND EXISTS ("""+guard+""")""",
                        (expected_revision,utc_at,slot['local_date'],
                         slot['local_time'],preview['timezone'],now,
                         principal.subject_id,proposal_token,tenant,request_id,
                         expected_proposal_token,tenant,request_id,
                         expected_revision))
                if changed.rowcount!=1:
                    raise ValueError('Proposal or draft changed; refresh before proposing')
        except sqlite3.IntegrityError as exc:
            raise ValueError('Proposed time already used by this business') from exc
        return {'tenant_id':tenant,'request_id':request_id,
                'utc_at':utc_at,'proposal_token':proposal_token,
                'status':'proposal_only',
                'posts_scheduled':0,'publishing_enabled':False}

    def suggest_unassigned(self, *, token, now):
        """Read-only, draft-only options; never persist or schedule a post.

        Assign each unassigned held draft a distinct, currently valid Manual
        preference slot in stable priority order. Even stale saved proposals
        reserve their own slots until a permitted editor explicitly removes
        them, so a preview cannot silently overwrite another editor's work.
        """
        principal = self._authorize(token=token, now=now,
                                    action=Action.READ_DRAFTS)
        tenant = principal.tenant_id
        drafts = self.content_service.list_for_business(
            token=token, tenant_id=tenant, now=now)
        if len(drafts)>5000:
            raise ValueError('Too many held drafts for safe calendar preview')
        assigned = self.db.execute(
            "SELECT request_id,utc_at FROM bam_calendar_proposals "
            "WHERE tenant_id=? ORDER BY utc_at LIMIT 201",
            (tenant,)).fetchall()
        if len(assigned)>200:
            raise ValueError('Too many saved proposals')
        assigned_ids = {row[0] for row in assigned}
        occupied = {row[1] for row in assigned}
        unassigned = sorted(
            (item for item in drafts
             if item['status'] in ('needs_content','ready_for_review')
             and item['request_id'] not in assigned_ids),
            key=lambda item: (-item['priority'], item['created_at'],
                              item['request_id']))
        preview = self._preview(token=token, tenant=tenant, now=now)
        slots = ([slot for slot in preview['slots']
                  if slot['utc_at'] not in occupied]
                 if preview['status']=='manual_preview' else [])
        items = [{
            'request_id':draft['request_id'],
            'draft_revision':draft['revision'],
            'utc_at':slot['utc_at'],
            'local_date':slot['local_date'],
            'local_time':slot['local_time'],
            'timezone':preview['timezone'],
            'publishing_enabled':False
        } for draft,slot in zip(unassigned[:20],slots[:20])]
        return {
            'tenant_id':tenant,'status':'suggestion_preview_only',
            'preference_status':preview['status'],
            'unassigned_held_count':len(unassigned),
            'available_slot_count':len(slots),
            'items':items,'posts_scheduled':0,'publishing_enabled':False
        }

    def discard(self,*,token,now,request_id,expected_proposal_token):
        principal=self._authorize(token=token,now=now,
                                   action=Action.EDIT_DRAFT)
        if (type(request_id) is not str or _ID.fullmatch(request_id) is None
                or type(expected_proposal_token) is not str or
                _ID.fullmatch(expected_proposal_token) is None):
            raise ValueError('Validated draft proposal version required')
        with self.db:
            deleted=self.db.execute("""DELETE FROM bam_calendar_proposals
                WHERE tenant_id=? AND request_id=? AND proposal_token=?""",
                (principal.tenant_id,request_id,expected_proposal_token))
            if deleted.rowcount!=1:
                raise ValueError('Proposal changed; refresh before removing date')
        return {'tenant_id':principal.tenant_id,
                'request_id':request_id,'removed':deleted.rowcount,
                'status':'proposal_only','posts_scheduled':0,
                'publishing_enabled':False}
