"""Offline owner approval intent ledger. Never grants publishing access."""
import hashlib
import sqlite3
import time
import uuid
from access_policy import Role
from truthguard_review_receipt import validate_review_receipt

class ApprovalIntentService:
    def __init__(self,*,db,sessions,directory,content_service):
        self.db=db
        self.sessions=sessions
        self.directory=directory
        self.content_service=content_service
        db.execute("""CREATE TABLE IF NOT EXISTS approval_intents (
            intent_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
            request_id TEXT NOT NULL, draft_sha256 TEXT NOT NULL,
            receipt_sha256 TEXT NOT NULL, approved_by TEXT NOT NULL,
            created_at INTEGER NOT NULL, revoked_at INTEGER)""")
        db.commit()

    def _owner(self,token,tenant_id,now):
        session=self.sessions.resolve(token,now=now)
        if session is None or session.principal.tenant_id!=tenant_id:
            raise PermissionError('Authenticated owner required')
        member=self.directory.resolve(tenant_id,session.principal.subject_id)
        if member is None or member.role!=Role.OWNER:
            raise PermissionError('Active owner required')
        return member.subject_id

    def record(self,*,token,tenant_id,request_id,receipt,now=None):
        timestamp=int(time.time()) if now is None else now
        actor=self._owner(token,tenant_id,timestamp)
        request=self.content_service.get(token=token,tenant_id=tenant_id,
                                         request_id=request_id,now=timestamp)
        if request is None:
            raise KeyError('Content request not found')
        if request['status']!='ready_for_review':
            raise ValueError('Required content not complete')
        if not validate_review_receipt(receipt=receipt,tenant_id=tenant_id,
                 request_id=request_id,draft_text=request['draft_text']):
            raise ValueError('Invalid or stale review receipt')
        intent_id=uuid.uuid4().hex
        with self.db:
            self.db.execute("""INSERT INTO approval_intents VALUES (?,?,?,?,?,?,?,NULL)""",
                (intent_id,tenant_id,request_id,
                 hashlib.sha256(request['draft_text'].encode('utf-8')).hexdigest(),
                 receipt['receipt_sha256'],actor,timestamp))
        return {'intent_id':intent_id,'status':'recorded_for_review',
                'publishing_enabled':False}

    def revoke(self,*,token,tenant_id,intent_id,now=None):
        timestamp=int(time.time()) if now is None else now
        self._owner(token,tenant_id,timestamp)
        with self.db:
            cursor=self.db.execute("""UPDATE approval_intents SET revoked_at=?
                WHERE tenant_id=? AND intent_id=? AND revoked_at IS NULL""",
                (timestamp,tenant_id,intent_id))
        return cursor.rowcount==1

    def inspect(self,*,token,tenant_id,intent_id,now=None):
        timestamp=int(time.time()) if now is None else now
        self._owner(token,tenant_id,timestamp)
        row=self.db.execute("""SELECT request_id,draft_sha256,revoked_at
            FROM approval_intents WHERE tenant_id=? AND intent_id=?""",
            (tenant_id,intent_id)).fetchone()
        if row is None:
            raise KeyError('Approval intent not found')
        request=self.content_service.get(token=token,tenant_id=tenant_id,
                                         request_id=row[0],now=timestamp)
        current=(request is not None and
                 hashlib.sha256(request['draft_text'].encode('utf-8')).hexdigest()==row[1])
        return {'intent_id':intent_id,'request_id':row[0],
                'active':row[2] is None,'draft_unchanged':current,
                'publishing_enabled':False}
