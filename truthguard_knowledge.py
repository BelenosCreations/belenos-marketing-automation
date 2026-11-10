"""TruthGuard: tenant-scoped, explicitly approved business facts.

Offline prototype. Only approved facts are usable as evidence; no AI inference.
"""
import sqlite3
import uuid
from datetime import datetime,timezone

class TruthGuardKnowledge:
    def __init__(self,db):
        self.db=db
        db.execute("""CREATE TABLE IF NOT EXISTS truthguard_facts (
          tenant_id TEXT NOT NULL, fact_id TEXT NOT NULL, claim_key TEXT NOT NULL,
          value TEXT NOT NULL, source TEXT NOT NULL, approved_by TEXT NOT NULL,
          approved_at INTEGER NOT NULL, expires_at INTEGER, revoked_at INTEGER,
          PRIMARY KEY(tenant_id,fact_id))""")
        db.execute("""CREATE INDEX IF NOT EXISTS truthguard_facts_lookup
          ON truthguard_facts(tenant_id,claim_key,revoked_at)""")
        db.commit()

    def approve(self,*,tenant_id,claim_key,value,source,approved_by,now,expires_at=None):
        if not all(isinstance(x,str) and x.strip() for x in
                   (tenant_id,claim_key,value,source,approved_by)):
            raise ValueError('Complete approved fact and provenance required')
        if type(now) is not int or (expires_at is not None and
                                   (type(expires_at) is not int or expires_at<=now)):
            raise ValueError('Invalid fact timestamps')
        fact_id=uuid.uuid4().hex
        self.db.execute("""INSERT INTO truthguard_facts
          (tenant_id,fact_id,claim_key,value,source,approved_by,approved_at,expires_at)
          VALUES (?,?,?,?,?,?,?,?)""",
          (tenant_id,fact_id,claim_key,value,source,approved_by,now,expires_at))
        self.db.commit()
        return fact_id

    def lookup(self,*,tenant_id,claim_key,now):
        return [{'fact_id':row[0],'value':row[1],'source':row[2],
                 'approved_at':row[3],'expires_at':row[4]}
                for row in self.db.execute("""SELECT fact_id,value,source,approved_at,expires_at
                FROM truthguard_facts WHERE tenant_id=? AND claim_key=?
                AND revoked_at IS NULL AND approved_at<=? AND (expires_at IS NULL OR expires_at>?)
                ORDER BY approved_at DESC,fact_id DESC""",(tenant_id,claim_key,now,now))]

    def revoke(self,*,tenant_id,fact_id,now):
        cursor=self.db.execute("""UPDATE truthguard_facts SET revoked_at=?
          WHERE tenant_id=? AND fact_id=? AND revoked_at IS NULL""",
          (now,tenant_id,fact_id))
        self.db.commit()
        return cursor.rowcount==1
