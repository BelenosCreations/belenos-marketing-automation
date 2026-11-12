"""Explicit offline Postgres preview for held drafts and AI budget data.

No OpenAI call, payment, subscription, provider key, migration execution or
social publishing. CI-only migration stage can execute these statements in
a disposable Postgres container, never on real Neon production.
"""
import sqlite3

_TABLES=(
 ('bam_ai_business_facts',(
    'tenant_id','facts_json','revision','confirmed_by','confirmed_at'),
  """CREATE TABLE bam_ai_business_facts (
    tenant_id TEXT PRIMARY KEY,facts_json TEXT NOT NULL,
    revision INTEGER NOT NULL,confirmed_by TEXT NOT NULL,
    confirmed_at BIGINT NOT NULL)"""),
 ('bam_ai_draft_components',(
    'tenant_id','subject_id','draft_id','platform','post_text','image_prompt',
    'needs_media','revision','created_at','updated_at'),
  """CREATE TABLE bam_ai_draft_components (
    tenant_id TEXT NOT NULL,subject_id TEXT NOT NULL,
    draft_id TEXT NOT NULL,platform TEXT NOT NULL,
    post_text TEXT NOT NULL,image_prompt TEXT,
    needs_media INTEGER NOT NULL,revision INTEGER NOT NULL,
    created_at BIGINT NOT NULL,updated_at BIGINT NOT NULL,
    PRIMARY KEY(tenant_id,subject_id,draft_id))"""),
 ('bam_ai_draft_verified_media',(
    'tenant_id','subject_id','draft_id','attachment_id','updated_at'),
  """CREATE TABLE bam_ai_draft_verified_media (
    tenant_id TEXT NOT NULL,subject_id TEXT NOT NULL,
    draft_id TEXT NOT NULL,attachment_id TEXT NOT NULL,
    updated_at BIGINT NOT NULL,
    PRIMARY KEY(tenant_id,subject_id,draft_id))"""),
 ('bam_ai_cost_events',(
    'event_id','tenant_id','subject_id','provider','model','input_tokens',
    'output_tokens','estimated_micro_usd','occurred_at','trusted_usage_hash'),
  """CREATE TABLE bam_ai_cost_events (
    event_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,subject_id TEXT NOT NULL,
    provider TEXT NOT NULL,model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,output_tokens INTEGER NOT NULL,
    estimated_micro_usd BIGINT NOT NULL,
    occurred_at BIGINT NOT NULL,trusted_usage_hash TEXT)"""),
 ('bam_ai_generation_requests',(
    'tenant_id','subject_id','request_key','request_fingerprint',
    'status','draft_id','created_at'),
  """CREATE TABLE bam_ai_generation_requests (
    tenant_id TEXT NOT NULL,subject_id TEXT NOT NULL,
    request_key TEXT NOT NULL,request_fingerprint TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN
       ('in_progress','completed','failed')),
    draft_id TEXT,created_at BIGINT NOT NULL,
    PRIMARY KEY(tenant_id,subject_id,request_key))"""),
 ('bam_ai_tenant_usage',(
    'tenant_id','month','accepted','reserved_micro_usd',
    'unpriced_requests'),
  """CREATE TABLE bam_ai_tenant_usage (
    tenant_id TEXT NOT NULL,month TEXT NOT NULL,
    accepted INTEGER NOT NULL DEFAULT 0,
    reserved_micro_usd BIGINT NOT NULL DEFAULT 0,
    unpriced_requests INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(tenant_id,month))"""),
 ('bam_ai_operator_usage',(
    'month','accepted','reserved_micro_usd','unpriced_requests'),
  """CREATE TABLE bam_ai_operator_usage (
    month TEXT PRIMARY KEY,accepted INTEGER NOT NULL DEFAULT 0,
    reserved_micro_usd BIGINT NOT NULL DEFAULT 0,
    unpriced_requests INTEGER NOT NULL DEFAULT 0)"""),
 ('bam_ai_operator_control',(
    'control_id','paused','updated_at'),
  """CREATE TABLE bam_ai_operator_control (
    control_id INTEGER PRIMARY KEY CHECK(control_id=1),
    paused INTEGER NOT NULL CHECK(paused IN (0,1)),
    updated_at BIGINT NOT NULL)"""),
)
BUDGET_TABLE_NAMES=tuple(name for name,_,_ in _TABLES)

def ai_budget_ddl_preview():
    """Stage 4 follows stage 3's original SQLite-style AI usage columns."""
    return (
        """ALTER TABLE bam_ai_usage ADD COLUMN reserved_micro_usd
            BIGINT NOT NULL DEFAULT 0""",
        """ALTER TABLE bam_ai_usage ADD COLUMN unpriced_requests
            INTEGER NOT NULL DEFAULT 0""",
    )+tuple(ddl for _,_,ddl in _TABLES)+(
        """CREATE INDEX bam_ai_cost_scope ON bam_ai_cost_events
            (tenant_id,subject_id,occurred_at)""",
        """CREATE UNIQUE INDEX bam_ai_cost_trusted_ref
            ON bam_ai_cost_events(tenant_id,subject_id,trusted_usage_hash)
            WHERE trusted_usage_hash IS NOT NULL""",
        # Fail-closed for future staged environments; unlike legacy local
        # SQLite scaffolding, never pre-authorize sponsored API requests.
        """INSERT INTO bam_ai_operator_control
            (control_id,paused,updated_at) VALUES (1,1,0)""",
    )

def inspect_ai_budget_sqlite(db):
    """Inspect existing *post-sponsorship-init* SQLite tables; no row values."""
    if not isinstance(db,sqlite3.Connection):
        raise TypeError('Trusted local SQLite connection required')
    report=[]
    for name,cols,_ in _TABLES:
        actual=tuple(row[1] for row in db.execute(
            'PRAGMA table_info("'+name+'")').fetchall())
        if actual!=cols:
            raise ValueError('AI budget source-schema mismatch: '+name)
        report.append({'table':name,'columns':len(cols),
                       'rows':db.execute('SELECT COUNT(*) FROM "'+name+'"'
                                  ).fetchone()[0]})
    usage=tuple(row[1] for row in db.execute(
        'PRAGMA table_info("bam_ai_usage")').fetchall())
    if usage!=('tenant_id','subject_id','month','accepted',
              'reserved_micro_usd','unpriced_requests'):
        raise ValueError('AI user monthly-budget source mismatch')
    return {'status':'ai_budget_schema_preview_only',
            'table_count':len(report),'tables':report,
            'user_usage_columns':len(usage),
            'provider_traffic':False,'real_cost_reconciliation':False,
            'data_exported':False,'publishing_enabled':False,
            'production_ready':False}
