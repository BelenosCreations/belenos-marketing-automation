"""Business-private editorial feedback notes on unpublished held drafts.

Feedback is not approval. Records carry independent compare-and-set tokens and
the draft revision reviewed; stale remarks remain visible but never confer
readiness, approval, a scheduled job or publication.
"""
import re
import sqlite3
import uuid
from access_policy import Action, Resource, Role, require_permission

_ID=re.compile(r'[a-f0-9]{32}\Z')
_ALLOWED_REVIEWERS=frozenset((Role.OWNER,Role.MARKETING_MANAGER))

class ReviewFeedback:
    def __init__(self, *, db, sessions, directory, content_service):
        self.db=db
        self.sessions=sessions
        self.directory=directory
        self.content_service=content_service
        db.execute("""CREATE TABLE IF NOT EXISTS bam_review_feedback(
            tenant_id TEXT NOT NULL,
            request_id TEXT NOT NULL,
            draft_revision INTEGER NOT NULL,
            note TEXT NOT NULL,
            feedback_token TEXT NOT NULL,
            updated_at INTEGER NOT NULL,
            updated_by TEXT NOT NULL,
            PRIMARY KEY(tenant_id,request_id))""")
        db.execute("""CREATE TABLE IF NOT EXISTS bam_review_feedback_events(
            event_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            request_id TEXT NOT NULL,
            action TEXT NOT NULL CHECK(action IN
                ('created','updated','removed')),
            draft_revision INTEGER NOT NULL,
            occurred_at INTEGER NOT NULL,
            actor_id TEXT NOT NULL)""")
        db.execute("""CREATE INDEX IF NOT EXISTS
            bam_review_feedback_events_business_time
            ON bam_review_feedback_events
            (tenant_id,occurred_at DESC,event_id DESC)""")
        db.commit()

    def _current(self, *, token, now, editing=False):
        if type(now) is not int or now<0:
            raise ValueError('Trusted server time required')
        session=self.sessions.resolve_current(
            token,directory=self.directory,now=now)
        if session is None:
            raise PermissionError('Active BAM session required')
        actor=session.principal
        require_permission(actor,Action.READ_DRAFTS,Resource(actor.tenant_id))
        if editing and actor.role not in _ALLOWED_REVIEWERS:
            raise PermissionError('Owner or marketing manager required')
        return actor

    @staticmethod
    def _valid_id(value):
        return type(value) is str and _ID.fullmatch(value) is not None

    def list_current_business(self, *, token, now):
        actor=self._current(token=token,now=now)
        rows=self.db.execute("""SELECT request_id,draft_revision,note,
            feedback_token,updated_at FROM bam_review_feedback
            WHERE tenant_id=? ORDER BY updated_at DESC,request_id LIMIT 201""",
            (actor.tenant_id,)).fetchall()
        if len(rows)>200:
            raise ValueError('Review feedback list too large')
        items=[]
        for rid,revision,note,version,updated_at in rows:
            current=self.content_service.get(
                token=token,tenant_id=actor.tenant_id,
                request_id=rid,now=now)
            if current is None:
                # Do not reveal notes attached to content removed by
                # trusted administration. No automatic destructive cleanup.
                continue
            items.append({'request_id':rid,'draft_revision':revision,
                 'current_revision':current['revision'],
                 'stale':current['revision']!=revision,
                 'note':note,'feedback_token':version,
                 'updated_at':updated_at,
                 'approval_granted':False,'publishing_enabled':False})
        return {'tenant_id':actor.tenant_id,'status':'feedback_only',
                'items':items,'approval_granted':False,
                'publishing_enabled':False}

    def history_current_business(self, *, token, now):
        """Recent event metadata only; no previous/current note text."""
        actor=self._current(token=token,now=now,editing=True)
        rows=self.db.execute("""SELECT event_id,request_id,action,
            draft_revision,occurred_at FROM bam_review_feedback_events
            WHERE tenant_id=? ORDER BY occurred_at DESC,event_id DESC
            LIMIT 51""",(actor.tenant_id,)).fetchall()
        return {'tenant_id':actor.tenant_id,
                'status':'feedback_history_only',
                'events':[{'event_id':event_id,'request_id':rid,
                     'action':action,'draft_revision':revision,
                     'occurred_at':at}
                     for event_id,rid,action,revision,at in rows[:50]],
                'truncated':len(rows)>50,
                'approval_granted':False,
                'publishing_enabled':False}

    def save(self, *, token, now, request_id, expected_revision,
             expected_feedback_token, note):
        actor=self._current(token=token,now=now,editing=True)
        if (not self._valid_id(request_id) or
            type(expected_revision) is not int or expected_revision<1 or
            (expected_feedback_token is not None and
             not self._valid_id(expected_feedback_token)) or
            type(note) is not str or note!=note.strip() or
            not 1<=len(note)<=1000 or
            any(ord(ch)<32 and ch not in '\n\t' for ch in note)):
            raise ValueError('Valid editorial note and draft revision required')
        draft=self.content_service.get(token=token,
            tenant_id=actor.tenant_id,request_id=request_id,now=now)
        if draft is None:
            raise KeyError('Draft unavailable')
        if draft['revision']!=expected_revision:
            raise ValueError('Draft changed; refresh feedback')
        new_version=uuid.uuid4().hex
        try:
            with self.db:
                current=self.content_service.requests.get(
                    tenant_id=actor.tenant_id,request_id=request_id)
                if current is None or current['revision']!=expected_revision:
                    raise ValueError('Draft changed; refresh feedback')
                if expected_feedback_token is None:
                    self.db.execute("""INSERT INTO bam_review_feedback
                        (tenant_id,request_id,draft_revision,note,
                         feedback_token,updated_at,updated_by)
                        VALUES (?,?,?,?,?,?,?)""",
                        (actor.tenant_id,request_id,expected_revision,note,
                         new_version,now,actor.subject_id))
                else:
                    changed=self.db.execute("""UPDATE bam_review_feedback
                        SET draft_revision=?,note=?,feedback_token=?,
                            updated_at=?,updated_by=?
                        WHERE tenant_id=? AND request_id=?
                          AND feedback_token=?""",
                        (expected_revision,note,new_version,now,
                         actor.subject_id,actor.tenant_id,request_id,
                         expected_feedback_token))
                    if changed.rowcount!=1:
                        raise ValueError('Feedback changed; refresh required')
                self.db.execute("""INSERT INTO bam_review_feedback_events
                    (event_id,tenant_id,request_id,action,draft_revision,
                     occurred_at,actor_id) VALUES (?,?,?,?,?,?,?)""",
                    (uuid.uuid4().hex,actor.tenant_id,request_id,
                     'created' if expected_feedback_token is None else 'updated',
                     expected_revision,now,actor.subject_id))
        except sqlite3.IntegrityError as error:
            raise ValueError('Feedback changed; refresh required') from error
        return {'tenant_id':actor.tenant_id,'request_id':request_id,
                'draft_revision':expected_revision,
                'feedback_token':new_version,'status':'feedback_only',
                'approval_granted':False,'publishing_enabled':False}

    def discard(self, *, token, now, request_id, expected_feedback_token):
        actor=self._current(token=token,now=now,editing=True)
        if (not self._valid_id(request_id) or
            not self._valid_id(expected_feedback_token)):
            raise ValueError('Current feedback version required')
        with self.db:
            existing=self.db.execute("""SELECT draft_revision
                FROM bam_review_feedback WHERE tenant_id=? AND request_id=?
                AND feedback_token=?""",
                (actor.tenant_id,request_id,
                 expected_feedback_token)).fetchone()
            if existing is None:
                raise ValueError('Feedback changed; refresh required')
            changed=self.db.execute("""DELETE FROM bam_review_feedback
                WHERE tenant_id=? AND request_id=? AND feedback_token=?""",
                (actor.tenant_id,request_id,expected_feedback_token))
            if changed.rowcount!=1:
                raise ValueError('Feedback changed; refresh required')
            self.db.execute("""INSERT INTO bam_review_feedback_events
                (event_id,tenant_id,request_id,action,draft_revision,
                 occurred_at,actor_id) VALUES (?,?,?,?,?,?,?)""",
                (uuid.uuid4().hex,actor.tenant_id,request_id,
                 'removed',existing[0],now,actor.subject_id))
        return {'tenant_id':actor.tenant_id,'request_id':request_id,
                'removed':1,'status':'feedback_only',
                'approval_granted':False,'publishing_enabled':False}
