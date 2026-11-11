"""Durable per-business AI generation request deduplication (SQLite foundation).

A claimed request key cannot be replayed to consume a second sponsored quota.
Ambiguous failed/in-progress requests are held for manual reconciliation, not
automatically retried. A production multi-worker deployment needs durable
shared storage and a recovery policy.
"""
import re

class AIGenerationIdempotency:
    def __init__(self, *, db, policy_store):
        self.db=db
        self.policy=policy_store
        db.execute("""CREATE TABLE IF NOT EXISTS bam_ai_generation_requests(
            tenant_id TEXT NOT NULL,subject_id TEXT NOT NULL,
            request_key TEXT NOT NULL,
            request_fingerprint TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN
                ('in_progress','completed','failed')),
            draft_id TEXT,created_at INTEGER NOT NULL,
            PRIMARY KEY(tenant_id,subject_id,request_key))""")
        db.commit()

    def claim(self, *, token, now, request_key, fingerprint):
        principal=self.policy._editor(token,now)
        if type(request_key) is not str or re.fullmatch(
            r'[0-9a-f]{32}',request_key) is None:
            raise ValueError('Random 32-character request key required')
        if type(fingerprint) is not str or re.fullmatch(
            r'[0-9a-f]{64}',fingerprint) is None:
            raise ValueError('Request fingerprint required')
        with self.db:
            cursor=self.db.execute("""INSERT OR IGNORE INTO
                bam_ai_generation_requests
                (tenant_id,subject_id,request_key,request_fingerprint,
                 status,draft_id,created_at)
                VALUES(?,?,?,?,'in_progress',NULL,?)""",
                (principal.tenant_id,principal.subject_id,request_key,
                 fingerprint,now))
            row=self.db.execute("""SELECT request_fingerprint,status,draft_id
                FROM bam_ai_generation_requests WHERE
                tenant_id=? AND subject_id=? AND request_key=?""",
                (principal.tenant_id,principal.subject_id,
                 request_key)).fetchone()
        if row[0]!=fingerprint:
            raise ValueError('Request key reused with different input')
        return {'claimed':cursor.rowcount==1,'status':row[1],
                'draft_id':row[2] if row[1]=='completed' else None}

    def status(self, *, token, now, request_key):
        """Read only the caller's request state; no automatic retry."""
        principal=self.policy._principal(token,now)
        if type(request_key) is not str or re.fullmatch(
            r'[0-9a-f]{32}',request_key) is None:
            raise ValueError('Valid request key required')
        row=self.db.execute("""SELECT status,draft_id FROM
            bam_ai_generation_requests WHERE tenant_id=? AND
            subject_id=? AND request_key=?""",
            (principal.tenant_id,principal.subject_id,request_key)).fetchone()
        if row is None:
            return {'found':False,'status':None,'draft_id':None,
                    'publishing_enabled':False}
        return {'found':True,'status':row[0],
                'draft_id':row[1] if row[0]=='completed' else None,
                'publishing_enabled':False}

    def finish(self, *, token, now, request_key, status, draft_id=None):
        principal=self.policy._editor(token,now)
        if status not in ('completed','failed') or (
            status=='completed' and (
                type(draft_id) is not str or re.fullmatch(
                    r'[0-9a-f]{32}',draft_id) is None)) or (
            status=='failed' and draft_id is not None):
            raise ValueError('Invalid terminal request state')
        with self.db:
            cursor=self.db.execute("""UPDATE bam_ai_generation_requests
                SET status=?,draft_id=? WHERE
                tenant_id=? AND subject_id=? AND request_key=?
                AND status='in_progress'""",
                (status,draft_id,principal.tenant_id,principal.subject_id,
                 request_key))
        if cursor.rowcount!=1:
            raise ValueError('Generation request not in progress')
