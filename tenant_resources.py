"""Fail-closed tenant ownership registry for legacy offline content.

Transitional layer: production must put tenant_id on each content table,
enforce foreign keys, and use transactional tenant-filtered queries.
"""
import sqlite3

class TenantResources:
    def __init__(self, db: sqlite3.Connection):
        self.db=db
        self.db.execute("""CREATE TABLE IF NOT EXISTS tenant_resources (
            kind TEXT NOT NULL CHECK(kind IN ('post','event')),
            resource_id TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            PRIMARY KEY(kind, resource_id)
        )""")
        self.db.commit()

    def register(self, *, kind: str, resource_id: str, tenant_id: str):
        """Trusted ingestion only; never expose to a client as an ownership claim."""
        if kind not in ('post','event') or not resource_id or not tenant_id:
            raise ValueError('Valid resource kind, ID and tenant required')
        table='posts' if kind=='post' else 'discovered_events'
        if not self.db.execute(f'SELECT 1 FROM {table} WHERE id=?',(resource_id,)).fetchone():
            raise ValueError('Resource does not exist')
        try:
            self.db.execute('INSERT INTO tenant_resources VALUES (?,?,?)',(kind,resource_id,tenant_id))
            self.db.commit()
        except sqlite3.IntegrityError as exc:
            raise PermissionError('Resource ownership is immutable') from exc

    def require(self, *, kind: str, resource_id: str, tenant_id: str):
        if not kind or not resource_id or not tenant_id:
            raise PermissionError('Missing tenant ownership')
        row=self.db.execute('SELECT tenant_id FROM tenant_resources WHERE kind=? AND resource_id=?',(kind,resource_id)).fetchone()
        if row is None or row[0]!=tenant_id:
            raise PermissionError('Resource not owned by tenant')
