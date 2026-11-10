"""Tenant-isolated, offline content requests and draft holding queue.

A content request never grants publication or scheduling permission. Uploaded
media is represented by trusted references; this module does not store files.
"""
import sqlite3
import uuid

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
            provided_items TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL CHECK(status IN
                ('needs_content','ready_for_review','postponed','unavailable')),
            priority INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )""")
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
                 required_items,provided_items,status,priority,created_at,updated_at)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (request_id,tenant_id,channel,draft_text,suggestion,
                 '\n'.join(required_items),'','needs_content',priority,now,now))
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
                    suggestion=row[3],required_items=row[4].split('\n'),
                    provided_items=row[5].split('\n') if row[5] else [],
                    status=row[6],priority=row[7],created_at=row[8],updated_at=row[9])

    def list_for_business(self, *, tenant_id, status=None):
        self._require(tenant_id)
        if status is not None and status not in STATUSES:
            raise ValueError('Invalid status')
        rows=self.db.execute("""SELECT request_id FROM content_requests
            WHERE tenant_id=? AND (? IS NULL OR status=?)
            ORDER BY priority DESC,created_at,request_id""",
            (tenant_id,status,status)).fetchall()
        return [self.get(tenant_id=tenant_id,request_id=row[0]) for row in rows]

    def provide(self, *, tenant_id, request_id, item, now):
        self._require(tenant_id,request_id,item)
        if type(now) is not int:
            raise ValueError('Invalid timestamp')
        request=self.get(tenant_id=tenant_id,request_id=request_id)
        if request is None:
            raise KeyError('Request not found in business')
        if request['status'] in ('unavailable','postponed'):
            raise ValueError('Reactivate before supplying content')
        if item not in request['required_items']:
            raise ValueError('Item is not required for this draft')
        provided=set(request['provided_items'])
        provided.add(item)
        status=('ready_for_review' if provided==set(request['required_items'])
                else 'needs_content')
        with self.db:
            self.db.execute("""UPDATE content_requests
                SET provided_items=?,status=?,updated_at=?
                WHERE tenant_id=? AND request_id=?""",
                ('\n'.join(x for x in request['required_items'] if x in provided),
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
            self.db.execute("""UPDATE content_requests SET status=?,updated_at=?
                WHERE tenant_id=? AND request_id=?""",
                (status,now,tenant_id,request_id))
        return status
