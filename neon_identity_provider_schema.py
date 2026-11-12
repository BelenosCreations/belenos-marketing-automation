"""Seven additional offline SQLite→Postgres DDL previews for BAM.

This catalog stores only SQL table definitions. No provider keys, database
clients, user data, paid API requests, migrations or publishing actions.
"""
import sqlite3

_EXTRA=(
 ('bam_ai_preferences',(
    'tenant_id','subject_id','ai_mode','credential_ref','updated_at'),
  """CREATE TABLE bam_ai_preferences (
    tenant_id TEXT NOT NULL,subject_id TEXT NOT NULL,
    ai_mode TEXT NOT NULL CHECK(
      ai_mode IN ('bam_sponsored','own_openai_key')),
    credential_ref TEXT,updated_at BIGINT NOT NULL,
    PRIMARY KEY(tenant_id,subject_id))"""),
 ('bam_ai_memories',(
    'tenant_id','subject_id','memory_json','updated_at'),
  """CREATE TABLE bam_ai_memories (
    tenant_id TEXT NOT NULL,subject_id TEXT NOT NULL,
    memory_json TEXT NOT NULL,updated_at BIGINT NOT NULL,
    PRIMARY KEY(tenant_id,subject_id))"""),
 ('bam_ai_usage',(
    'tenant_id','subject_id','month','accepted'),
  """CREATE TABLE bam_ai_usage (
    tenant_id TEXT NOT NULL,subject_id TEXT NOT NULL,
    month TEXT NOT NULL,accepted INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(tenant_id,subject_id,month))"""),
 ('provider_connections',(
    'tenant_id','platform','account_id','vault_reference','scope','state',
    'expires_at','updated_at'),
  """CREATE TABLE provider_connections (
    tenant_id TEXT NOT NULL,platform TEXT NOT NULL,
    account_id TEXT NOT NULL,vault_reference TEXT NOT NULL,
    scope TEXT NOT NULL,state TEXT NOT NULL,
    expires_at BIGINT,updated_at BIGINT NOT NULL,
    PRIMARY KEY(tenant_id,platform,account_id))"""),
 ('bam_google_challenges',(
    'challenge_hash','nonce','expires_at','consumed_at'),
  """CREATE TABLE bam_google_challenges (
    challenge_hash TEXT PRIMARY KEY,nonce TEXT NOT NULL,
    expires_at BIGINT NOT NULL,consumed_at BIGINT)"""),
 ('oauth_attempts',(
    'state_hash','tenant_id','platform','account_id',
    'verifier_hash','expires_at','consumed_at'),
  """CREATE TABLE oauth_attempts (
    state_hash TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,
    platform TEXT NOT NULL,account_id TEXT NOT NULL,
    verifier_hash TEXT NOT NULL,expires_at BIGINT NOT NULL,
    consumed_at BIGINT)"""),
 ('content_attachments',(
    'attachment_id','tenant_id','request_id','item','media_type','sha256',
    'storage_key','status','created_at'),
  """CREATE TABLE content_attachments (
    attachment_id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,
    request_id TEXT NOT NULL,item TEXT NOT NULL,
    media_type TEXT NOT NULL,sha256 TEXT NOT NULL,
    storage_key TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending','verified','rejected')),
    created_at BIGINT NOT NULL,
    UNIQUE(tenant_id,request_id,item,attachment_id))"""),
)
EXTRA_TABLE_NAMES=tuple(name for name,_,_ in _EXTRA)

def identity_provider_ddl_preview():
    return tuple(ddl for _,_,ddl in _EXTRA)

def inspect_identity_provider_sqlite(db):
    """No customer rows, credential values or raw DDL included in report."""
    if not isinstance(db,sqlite3.Connection):
        raise TypeError('Initialized offline SQLite connection required')
    items=[]
    for table,columns,_ in _EXTRA:
        actual=tuple(row[1] for row in db.execute(
            'PRAGMA table_info("'+table+'")').fetchall())
        if actual!=columns:
            raise ValueError('Source schema drift requires review: '+table)
        count=db.execute('SELECT COUNT(*) FROM "'+table+'"').fetchone()[0]
        items.append({'table':table,'column_count':len(columns),'rows':count})
    return {'status':'seven_table_portability_preview',
            'table_count':len(items),'tables':items,
            'secrets_exposed':False,'data_exported':False,
            'provider_connected':False,'migration_executed':False,
            'production_ready':False,'publishing_enabled':False}
