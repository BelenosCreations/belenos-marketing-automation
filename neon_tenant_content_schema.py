"""Source-parity PostgreSQL DDL preview for legacy tenant content/setting rows.

These are OFFLINE schemas for test-only Postgres. A stored 'approved' status
is not social publication, a schedule job, or live provider authorization.
"""
import sqlite3

_DDL=(
 ('tenant_posts',('tenant_id','post_id','content','category','status'),
  """CREATE TABLE tenant_posts (
    tenant_id TEXT NOT NULL,post_id TEXT NOT NULL,
    content TEXT NOT NULL,category TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN
      ('draft','approval_required','approved','rejected','revoked')),
    PRIMARY KEY(tenant_id,post_id))"""),
 ('tenant_approvals',('tenant_id','post_id','actor_id','decision'),
  """CREATE TABLE tenant_approvals (
    tenant_id TEXT NOT NULL,post_id TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    decision TEXT NOT NULL CHECK(decision IN
      ('approved','rejected','revoked')),
    PRIMARY KEY(tenant_id,post_id),
    FOREIGN KEY(tenant_id,post_id)
      REFERENCES tenant_posts(tenant_id,post_id))"""),
 ('tenant_events',('tenant_id','event_id','title','state'),
  """CREATE TABLE tenant_events (
    tenant_id TEXT NOT NULL,event_id TEXT NOT NULL,
    title TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN
      ('unconfirmed','confirmed','rejected')),
    PRIMARY KEY(tenant_id,event_id))"""),
 ('scheduling_settings',(
    'tenant_id','mode','timezone_name','weekly_json',
    'preferred_hours_json','revision'),
  """CREATE TABLE scheduling_settings (
    tenant_id TEXT PRIMARY KEY,mode TEXT NOT NULL,
    timezone_name TEXT NOT NULL,weekly_json TEXT NOT NULL,
    preferred_hours_json TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1)"""),
)
TENANT_CONTENT_TABLES=tuple(name for name,_,_ in _DDL)


def tenant_content_ddl_preview():
    return tuple(sql for _,_,sql in _DDL)


def inspect_tenant_content_sqlite(db):
    """No draft copy, event title or saved scheduling preferences escape."""
    if not isinstance(db,sqlite3.Connection):
        raise TypeError('Trusted local SQLite source connection required')
    entries=[]
    for name,columns,_ in _DDL:
        actual=tuple(row[1] for row in db.execute(
            'PRAGMA table_info("'+name+'")'))
        if actual!=columns:
            raise ValueError('Local source schema drift: '+name)
        entries.append({'table':name,'columns':len(columns),
                        'rows':db.execute(
                            'SELECT COUNT(*) FROM "'+name+'"').fetchone()[0]})
    return {'status':'nonpublishing_content_schema_preview_only',
            'table_count':len(entries),'tables':entries,
            'private_data_exported':False,
            'hosted_database_connected':False,
            'scheduled_jobs_created':False,
            'social_publishing_enabled':False,'production_ready':False}
