"""Tenant-isolated, offline content requests and draft holding queue.

A content request never grants publication or scheduling permission. Uploaded
media is represented by trusted references; this module does not store files.
"""
import sqlite3
import uuid
import json

STATUSES=('needs_content','ready_for_review','postponed','unavailable')

class ContentRequests:
    def __init__(self, db):
        self.db=db
        db.execute("""CREATE TABLE IF NOT EXISTS content_requests (
            request_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            draft_text TEXT NOT NULL,
            suggestion TEXT NOT NULL,
            required_items TEXT NOT NULL,
            provided_items TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL CHECK(status IN
                ('needs_content','ready_for_review','postponed','unavailable')),
            priority INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )""")
        # Preserve existing local SQLite databases when upgrading old drafts.
        if 'revision' not in {row[1] for row in
                              db.execute('PRAGMA table_info(content_requests)')}:
            db.execute("""ALTER TABLE content_requests
                ADD COLUMN revision INTEGER NOT NULL DEFAULT 1""")
        db.commit()

    @staticmethod
    def _require(*values):
        if any(not isinstance(v,str) or not v.strip() for v in values):
            raise ValueError('Nonempty text fields required')

    def create(self, *, tenant_id, channel, draft_text, suggestion,
               required_items, now, priority=0):
        self._require(tenant_id,channel,draft_text,suggestion)
        if (not isinstance(required_items,(list,tuple)) or not required_items
                or any(not isinstance(x,str) or not x.strip() for x in required_items)
                or len(set(required_items))!=len(required_items)):
            raise ValueError('Unique required content items must be provided')
        if type(now) is not int or type(priority) is not int:
            raise ValueError('Invalid timestamp or priority')
        request_id=uuid.uuid4().hex
        with self.db:
            self.db.execute("""INSERT INTO content_requests
                (request_id,tenant_id,channel,draft_text,suggestion,
                 required_items,provided_items,status,priority,created_at,updated_at,revision)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (request_id,tenant_id,channel,draft_text,suggestion,
                 json.dumps(list(required_items)),'{}','needs_content',priority,now,now))
        return request_id

    def get(self, *, tenant_id, request_id):
        self._require(tenant_id,request_id)
        row=self.db.execute("""SELECT request_id,channel,draft_text,suggestion,
                required_items,provided_items,status,priority,created_at,updated_at
                FROM content_requests WHERE tenant_id=? AND request_id=?""",
                (tenant_id,request_id)).fetchone()
        if row is None:
            return None
        return dict(request_id=row[0],channel=row[1],draft_text=row[2],
                    suggestion=row[3],required_items=json.loads(row[4]),
                    provided_items=json.loads(row[5]),
                    status=row[6],priority=row[7],created_at=row[8],
                    updated_at=row[9],revision=row[10])

    def list_for_business(self, *, tenant_id, status=None):
        self._require(tenant_id)
        if status is not None and status not in STATUSES:
            raise ValueError('Invalid status')
        rows=self.db.execute("""SELECT request_id FROM content_requests
            WHERE tenant_id=? AND (? IS NULL OR status=?)
            ORDER BY priority DESC,created_at,request_id""",
            (tenant_id,status,status)).fetchall()
        return [self.get(tenant_id=tenant_id,request_id=row[0]) for row in rows]

    def provide(self, *, tenant_id, request_id, item, content_reference, now):
        self._require(tenant_id,request_id,item,content_reference)
        if type(now) is not int:
            raise ValueError('Invalid timestamp')
        request=self.get(tenant_id=tenant_id,request_id=request_id)
        if request is None:
            raise KeyError('Request not found in business')
        if request['status'] in ('unavailable','postponed'):
            raise ValueError('Reactivate before supplying content')
        if item not in request['required_items']:
            raise ValueError('Item is not required for this draft')
        provided=dict(request['provided_items'])
        provided[item]=content_reference
        status=('ready_for_review' if set(provided)==set(request['required_items'])
                else 'needs_content')
        with self.db:
            self.db.execute("""UPDATE content_requests
                SET provided_items=?,status=?,updated_at=?,revision=revision+1
                WHERE tenant_id=? AND request_id=?""",
                (json.dumps(provided,sort_keys=True),
                 status,now,tenant_id,request_id))
        return status

    def set_hold(self, *, tenant_id, request_id, status, now):
        if status not in ('postponed','unavailable','needs_content'):
            raise ValueError('Invalid hold status')
        request=self.get(tenant_id=tenant_id,request_id=request_id)
        if request is None:
            raise KeyError('Request not found in business')
        if status=='needs_content' and set(request['provided_items'])==set(request['required_items']):
            raise ValueError('Complete request must remain ready for review')
        with self.db:
            self.db.execute("""UPDATE content_requests SET status=?,updated_at=?,revision=revision+1
                WHERE tenant_id=? AND request_id=?""",
                (status,now,tenant_id,request_id))
        return status

    def revise(self, *, tenant_id, request_id, target,
               revised_text, expected_revision, now):
        """Optimistic, single-component edit; never changes media or status."""
        self._require(tenant_id,request_id)
        if target not in ('draft_text','suggestion'):
            raise ValueError('Only draft copy or guidance may be revised')
        if (type(revised_text) is not str or not revised_text.strip()
                or revised_text!=revised_text.strip()
                or len(revised_text)>2000
                or type(expected_revision) is not int
                or expected_revision<1 or type(now) is not int or now<0):
            raise ValueError('Invalid draft revision')
        # Column name comes exclusively from a server-side, fixed allowlist.
        with self.db:
            result=self.db.execute(
                f"""UPDATE content_requests SET {target}=?,
                       revision=revision+1,updated_at=?
                     WHERE tenant_id=? AND request_id=? AND revision=?""",
                (revised_text,now,tenant_id,request_id,expected_revision))
        if result.rowcount!=1:
            if self.get(tenant_id=tenant_id,request_id=request_id) is None:
                raise KeyError('Draft not found in business')
            raise ValueError('Stale draft revision')
        return self.get(tenant_id=tenant_id,request_id=request_id)
