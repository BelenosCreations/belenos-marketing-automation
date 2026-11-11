"""Tenant-scoped attachment metadata registry (offline prototype).

No file upload, malware scan, permission verification, or storage access is
implemented here. A reference becomes usable only after trusted validation.
"""
import sqlite3
import uuid

class AttachmentRegistry:
    def __init__(self, db):
        self.db=db
        db.execute("""CREATE TABLE IF NOT EXISTS content_attachments (
            attachment_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            request_id TEXT NOT NULL,
            item TEXT NOT NULL,
            media_type TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            storage_key TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('pending','verified','rejected')),
            created_at INTEGER NOT NULL,
            UNIQUE(tenant_id,request_id,item,attachment_id)
        )""")
        db.commit()

    def register_pending(self, *, tenant_id, request_id, item, media_type,
                         sha256, storage_key, now):
        if not all(isinstance(x,str) and x.strip() for x in
                   (tenant_id,request_id,item,media_type,sha256,storage_key)):
            raise ValueError('Required attachment metadata missing')
        if media_type not in ('image/jpeg','image/png','image/webp','video/mp4',
                              'text/plain','application/pdf'):
            raise ValueError('Unsupported media type')
        if len(sha256)!=64 or any(c not in '0123456789abcdef' for c in sha256):
            raise ValueError('Invalid SHA-256')
        if type(now) is not int:
            raise ValueError('Invalid timestamp')
        attachment_id=uuid.uuid4().hex
        with self.db:
            self.db.execute("""INSERT INTO content_attachments VALUES
                (?,?,?,?,?,?,?,?,?)""",(attachment_id,tenant_id,request_id,
                item,media_type,sha256,storage_key,'pending',now))
        return attachment_id

    def validate_trusted(self, *, tenant_id, attachment_id, approved):
        """Only an authenticated trusted scanner/permission worker may call."""
        if type(approved) is not bool:
            raise ValueError('Validation decision must be boolean')
        with self.db:
            result=self.db.execute("""UPDATE content_attachments SET status=?
                WHERE tenant_id=? AND attachment_id=? AND status='pending'""",
                ('verified' if approved else 'rejected',tenant_id,attachment_id))
        if result.rowcount!=1:
            raise KeyError('Pending attachment not found')

    def resolve_verified(self, *, tenant_id, request_id, item, attachment_id):
        row=self.db.execute("""SELECT attachment_id FROM content_attachments
            WHERE tenant_id=? AND request_id=? AND item=? AND attachment_id=?
              AND status='verified'""",
            (tenant_id,request_id,item,attachment_id)).fetchone()
        return row[0] if row else None
