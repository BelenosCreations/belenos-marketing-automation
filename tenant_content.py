"""Native tenant-scoped offline content store.

New development path, independent of legacy unscoped tables. All reads and
writes require tenant_id. No publishing integration or public API.
"""
import hashlib
import sqlite3

class TenantContentStore:
    def __init__(self, db: sqlite3.Connection):
        self.db=db
        db.execute("""CREATE TABLE IF NOT EXISTS tenant_posts (
            tenant_id TEXT NOT NULL,
            post_id TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('draft','approval_required','approved','rejected','revoked')),
            PRIMARY KEY (tenant_id, post_id)
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS tenant_approvals (
            tenant_id TEXT NOT NULL,
            post_id TEXT NOT NULL,
            actor_id TEXT NOT NULL,
            decision TEXT NOT NULL CHECK(decision IN ('approved','rejected','revoked')),
            PRIMARY KEY (tenant_id, post_id),
            FOREIGN KEY (tenant_id,post_id) REFERENCES tenant_posts(tenant_id,post_id)
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS tenant_events (
            tenant_id TEXT NOT NULL,
            event_id TEXT NOT NULL,
            title TEXT NOT NULL,
            state TEXT NOT NULL CHECK(state IN ('unconfirmed','confirmed','rejected')),
            PRIMARY KEY (tenant_id,event_id)
        )""")
        db.commit()

    @staticmethod
    def _required(*values):
        if any(not isinstance(v,str) or not v.strip() for v in values):
            raise ValueError('Nonempty string fields required')

    def create_post(self, tenant_id, post_id, content, category):
        self._required(tenant_id,post_id,content,category)
        self.db.execute('INSERT INTO tenant_posts VALUES (?,?,?,?,?)',
                        (tenant_id,post_id,content,category,'approval_required'))
        self.db.commit()

    def get_post(self, tenant_id, post_id):
        self._required(tenant_id,post_id)
        row=self.db.execute('SELECT content,category,status FROM tenant_posts WHERE tenant_id=? AND post_id=?',
                            (tenant_id,post_id)).fetchone()
        return row

    def decide_post(self, tenant_id, post_id, actor_id, decision):
        self._required(tenant_id,post_id,actor_id)
        if decision not in ('approved','rejected','revoked'):
            raise ValueError('Invalid decision')
        row=self.get_post(tenant_id,post_id)
        if row is None:
            raise PermissionError('Post not owned by tenant')
        self.db.execute('UPDATE tenant_posts SET status=? WHERE tenant_id=? AND post_id=?',
                        (decision,tenant_id,post_id))
        self.db.execute("""INSERT INTO tenant_approvals VALUES (?,?,?,?)
            ON CONFLICT(tenant_id,post_id) DO UPDATE SET actor_id=excluded.actor_id,
            decision=excluded.decision""",(tenant_id,post_id,actor_id,decision))
        self.db.commit()

    def create_event(self, tenant_id, event_id, title):
        self._required(tenant_id,event_id,title)
        self.db.execute('INSERT INTO tenant_events VALUES (?,?,?,?)',
                        (tenant_id,event_id,title,'unconfirmed'))
        self.db.commit()

    def decide_event(self, tenant_id, event_id, confirmed):
        self._required(tenant_id,event_id)
        cursor=self.db.execute('UPDATE tenant_events SET state=? WHERE tenant_id=? AND event_id=?',
                               ('confirmed' if confirmed else 'rejected',tenant_id,event_id))
        if cursor.rowcount!=1:
            raise PermissionError('Event not owned by tenant')
        self.db.commit()

    def get_event(self, tenant_id, event_id):
        self._required(tenant_id,event_id)
        return self.db.execute('SELECT title,state FROM tenant_events WHERE tenant_id=? AND event_id=?',
                               (tenant_id,event_id)).fetchone()
