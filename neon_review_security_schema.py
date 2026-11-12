"""Six review/security support tables for a test-only PostgreSQL preview.

This is NOT a production authorization ledger. Local fact reviews, editorial
queues, source attestations, credential reset tokens and approval intents
never create real emails, publishing permissions or executable jobs.
"""
import sqlite3

_REVIEW=(
 ('editorial_attestations',(
    'tenant_id','original_url','platform','account_id','identity_verified',
    'competitor_status','verified_at','expires_at'),
  """CREATE TABLE editorial_attestations (
    tenant_id TEXT NOT NULL,original_url TEXT NOT NULL,
    platform TEXT NOT NULL,account_id TEXT NOT NULL,
    identity_verified INTEGER NOT NULL CHECK(identity_verified IN (0,1)),
    competitor_status TEXT NOT NULL CHECK(
      competitor_status IN ('cleared','possible','unknown')),
    verified_at BIGINT NOT NULL,expires_at BIGINT NOT NULL,
    PRIMARY KEY(tenant_id,original_url))"""),
 ('editorial_inbox',(
    'tenant_id','platform','account_id','original_url','topic','summary',
    'status','reason','candidate_digest'),
  """CREATE TABLE editorial_inbox (
    tenant_id TEXT NOT NULL,platform TEXT NOT NULL,
    account_id TEXT NOT NULL,original_url TEXT NOT NULL,
    topic TEXT NOT NULL,summary TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('review','blocked')),
    reason TEXT NOT NULL,candidate_digest TEXT,
    PRIMARY KEY(tenant_id,original_url))"""),
 ('approval_intents',(
    'intent_id','tenant_id','request_id','draft_sha256','receipt_sha256',
    'approved_by','created_at','revoked_at','content_sha256'),
  """CREATE TABLE approval_intents (
    intent_id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,
    request_id TEXT NOT NULL,draft_sha256 TEXT NOT NULL,
    receipt_sha256 TEXT NOT NULL,approved_by TEXT NOT NULL,
    created_at BIGINT NOT NULL,revoked_at BIGINT,
    content_sha256 TEXT)"""),
 ('truthguard_facts',(
    'tenant_id','fact_id','claim_key','value','source','approved_by',
    'approved_at','expires_at','revoked_at'),
  """CREATE TABLE truthguard_facts (
    tenant_id TEXT NOT NULL,fact_id TEXT NOT NULL,
    claim_key TEXT NOT NULL,value TEXT NOT NULL,
    source TEXT NOT NULL,approved_by TEXT NOT NULL,
    approved_at BIGINT NOT NULL,expires_at BIGINT,
    revoked_at BIGINT,
    PRIMARY KEY(tenant_id,fact_id))"""),
 ('creator_identities',(
    'tenant_id','platform','account_id','status','reason'),
  """CREATE TABLE creator_identities (
    tenant_id TEXT NOT NULL,platform TEXT NOT NULL,
    account_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('approved','blocked','review')),
    reason TEXT NOT NULL,
    PRIMARY KEY(tenant_id,platform,account_id))"""),
 ('bam_email_actions',(
    'token_hash','subject_id','purpose','expires_at','consumed_at'),
  """CREATE TABLE bam_email_actions (
    token_hash TEXT PRIMARY KEY,subject_id TEXT NOT NULL,
    purpose TEXT NOT NULL CHECK(purpose IN ('verify','reset')),
    expires_at BIGINT NOT NULL,consumed_at BIGINT)"""),
)
REVIEW_SECURITY_TABLES=tuple(name for name,_,_ in _REVIEW)


def review_security_ddl_preview():
    return tuple(ddl for _,_,ddl in _REVIEW)+(
        """CREATE INDEX truthguard_facts_lookup
           ON truthguard_facts(tenant_id,claim_key,revoked_at)""",)


def inspect_review_security_sqlite(db):
    """Metadata only; no private facts, editorial URLs or reset token values."""
    if not isinstance(db,sqlite3.Connection):
        raise TypeError('Trusted local SQLite connection required')
    items=[]
    for name,columns,_ in _REVIEW:
        actual=tuple(row[1] for row in db.execute(
            'PRAGMA table_info("'+name+'")'))
        if actual!=columns:
            raise ValueError('Unexpected local review/security schema: '+name)
        items.append({'table':name,'columns':len(columns),
                      'rows':db.execute(
                          'SELECT COUNT(*) FROM "'+name+'"').fetchone()[0]})
    return {'status':'review_security_schema_preview_only',
            'table_count':len(items),'tables':items,
            'secret_data_exported':False,
            'real_email_delivery_enabled':False,
            'publish_permission_granted':False,
            'hosted_postgres_connected':False,
            'production_ready':False}
