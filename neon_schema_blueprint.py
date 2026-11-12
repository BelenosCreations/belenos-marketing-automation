"""Pure, offline blueprint for a *subset* of BAM's future Neon schema.

No database credentials, driver, connection, migration execution, or
network calls. Never use this to claim production PostgreSQL readiness:
more BAM tables, transactional logic, permissions, and restore tests remain.
"""
import hashlib
import json
import sqlite3

# Intentionally limited to identity + held-content foundations. The actual
# BAM schema contains additional tables that must be ported and vetted before
# any production application points at PostgreSQL.
_TABLES = (
 ('bam_identities', (
    'subject_id','email','email_verified','active','created_at'),
  """CREATE TABLE bam_identities (
    subject_id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    email_verified SMALLINT NOT NULL DEFAULT 0 CHECK (email_verified IN (0,1)),
    active SMALLINT NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
    created_at BIGINT NOT NULL)"""),
 ('bam_password_credentials',(
    'subject_id','salt','digest','iterations'),
  """CREATE TABLE bam_password_credentials (
    subject_id TEXT PRIMARY KEY REFERENCES bam_identities(subject_id),
    salt BYTEA NOT NULL,
    digest BYTEA NOT NULL,
    iterations INTEGER NOT NULL CHECK (iterations>0))"""),
 ('bam_google_identities',(
    'google_sub','subject_id'),
  """CREATE TABLE bam_google_identities (
    google_sub TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL UNIQUE REFERENCES bam_identities(subject_id))"""),
 ('members',(
    'tenant_id','subject_id','role','active','revision'),
  """CREATE TABLE members (
    tenant_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    role TEXT NOT NULL,
    active SMALLINT NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
    revision INTEGER NOT NULL DEFAULT 1 CHECK (revision>=1),
    PRIMARY KEY(tenant_id,subject_id))"""),
 ('sessions',(
    'token_hash','subject_id','tenant_id','role','expires_at','revoked_at'),
  """CREATE TABLE sessions (
    token_hash TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    role TEXT NOT NULL,
    expires_at BIGINT NOT NULL,
    revoked_at BIGINT)"""),
 ('bam_login_throttle',(
    'identity_hash','window_start','failures'),
  """CREATE TABLE bam_login_throttle (
    identity_hash TEXT PRIMARY KEY,
    window_start BIGINT NOT NULL,
    failures INTEGER NOT NULL CHECK (failures>=0))"""),
 ('content_requests',(
    'request_id','tenant_id','channel','draft_text','suggestion',
    'required_items','provided_items','status','priority','priority_token',
    'created_at','updated_at','revision'),
  """CREATE TABLE content_requests (
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
    priority_token TEXT NOT NULL DEFAULT '',
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1 CHECK (revision>=1))"""),
 ('bam_posting_preferences',(
    'tenant_id','mode','timezone','manual_times','updated_at','updated_by'),
  """CREATE TABLE bam_posting_preferences (
    tenant_id TEXT PRIMARY KEY,
    mode TEXT NOT NULL,
    timezone TEXT NOT NULL,
    manual_times TEXT NOT NULL,
    updated_at BIGINT NOT NULL,
    updated_by TEXT NOT NULL)"""),
 ('bam_calendar_proposals',(
    'tenant_id','request_id','draft_revision','utc_at','local_date',
    'local_time','timezone','updated_at','updated_by','proposal_token'),
  """CREATE TABLE bam_calendar_proposals (
    tenant_id TEXT NOT NULL,
    request_id TEXT NOT NULL,
    draft_revision INTEGER NOT NULL,
    utc_at TEXT NOT NULL,
    local_date TEXT NOT NULL,
    local_time TEXT NOT NULL,
    timezone TEXT NOT NULL,
    updated_at BIGINT NOT NULL,
    updated_by TEXT NOT NULL,
    proposal_token TEXT NOT NULL,
    PRIMARY KEY(tenant_id,request_id),
    UNIQUE(tenant_id,utc_at))"""),
)

TABLE_NAMES=tuple(name for name,_,_ in _TABLES)
NO_PROVIDER_OPERATIONS=True


def ddl_preview():
    """DDL text for human review ONLY; does not execute or open a database."""
    return tuple(sql for _,_,sql in _TABLES)


def inspect_sqlite_subset(db):
    """Validate existing offline schema and report metadata, never row values.

    Counts deliberately do not enumerate customer identities, draft content,
    password digests, session tokens or any credential material. This is a
    preflight for a future explicit migration, not the migration itself.
    """
    if not isinstance(db,sqlite3.Connection):
        raise TypeError('Offline SQLite connection required')
    result=[]
    for name,columns,_ in _TABLES:
        existing=tuple(row[1] for row in db.execute(
            'PRAGMA table_info("'+name+'")').fetchall())
        if set(existing)!=set(columns) or len(existing)!=len(columns):
            raise ValueError('Offline schema incompatible: '+name)
        row_count=db.execute('SELECT COUNT(*) FROM "'+name+'"').fetchone()[0]
        if type(row_count) is not int or row_count<0:
            raise ValueError('Invalid table row count')
        result.append({'table':name,'rows':row_count,'columns':len(columns)})
    digest=hashlib.sha256(json.dumps(
        [(n,cols) for n,cols,_ in _TABLES],
        separators=(',',':')).encode('utf-8')).hexdigest()
    return {'status':'partial_schema_preview_only',
            'target':'separate_neon_free_postgresql',
            'schema_contract_digest':digest,
            'tables':result,'subset_table_count':len(result),
            'data_exported':False,'postgres_connection_attempted':False,
            'live_migration_performed':False,
            'production_ready':False,'publishing_enabled':False,
            'remaining_gates':[
                'complete_all_other_tables',
                'postgres_driver_and_transaction_adapter',
                'tenant_access_isolation_tests',
                'typed_row_data_migration_and_integrity',
                'encrypted_backup_restore',
                'approved_private_staging'
            ]}


def assert_never_execute_preview(*,enabled=False):
    """Conspicuous no-op guard; no public migration switch exists."""
    raise PermissionError('PostgreSQL schema preview is not an executor')
