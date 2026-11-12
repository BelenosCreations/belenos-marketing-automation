"""Business research and imported-analytics PostgreSQL DDL *preview only*.

All statements are pre-defined. No customer records, external requests,
production DB connection, tracking, or live provider access.
"""
import sqlite3

_DATA=(
 ('business_profiles',('tenant_id','display_name','industry'),
  """CREATE TABLE business_profiles (
    tenant_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    industry TEXT NOT NULL)"""),
 ('business_topics',('tenant_id','topic'),
  """CREATE TABLE business_topics (
    tenant_id TEXT NOT NULL,topic TEXT NOT NULL,
    PRIMARY KEY(tenant_id,topic),
    FOREIGN KEY(tenant_id) REFERENCES business_profiles(tenant_id))"""),
 ('business_sources',(
    'tenant_id','source_url','source_name','topic','approved'),
  """CREATE TABLE business_sources (
    tenant_id TEXT NOT NULL,source_url TEXT NOT NULL,
    source_name TEXT NOT NULL,topic TEXT NOT NULL,
    approved INTEGER NOT NULL CHECK(approved IN (0,1)),
    PRIMARY KEY(tenant_id,source_url),
    FOREIGN KEY(tenant_id,topic) REFERENCES business_topics(tenant_id,topic))"""),
 ('business_competitors',('tenant_id','source_host','reason'),
  """CREATE TABLE business_competitors (
    tenant_id TEXT NOT NULL,source_host TEXT NOT NULL,
    reason TEXT NOT NULL,
    PRIMARY KEY(tenant_id,source_host))"""),
 ('analytics_sync_checkpoints',(
    'tenant_id','platform','account_id','cursor','updated_at'),
  """CREATE TABLE analytics_sync_checkpoints (
    tenant_id TEXT NOT NULL,platform TEXT NOT NULL,
    account_id TEXT NOT NULL,cursor TEXT NOT NULL,
    updated_at BIGINT NOT NULL,
    PRIMARY KEY(tenant_id,platform,account_id))"""),
 ('audience_observations',(
    'tenant_id','platform','source_post_id','candidate',
    'engagement_rate','measured_at','source_name'),
  """CREATE TABLE audience_observations (
    tenant_id TEXT NOT NULL,platform TEXT NOT NULL,
    source_post_id TEXT NOT NULL,candidate TEXT NOT NULL,
    engagement_rate DOUBLE PRECISION NOT NULL,
    measured_at BIGINT NOT NULL,source_name TEXT NOT NULL,
    PRIMARY KEY(tenant_id,platform,source_post_id))"""),
 ('tenant_resources',('kind','resource_id','tenant_id'),
  """CREATE TABLE tenant_resources (
    kind TEXT NOT NULL CHECK(kind IN ('post','event')),
    resource_id TEXT NOT NULL,tenant_id TEXT NOT NULL,
    PRIMARY KEY(kind,resource_id))"""),
)
BUSINESS_ANALYTICS_TABLES=tuple(name for name,_,_ in _DATA)


def business_analytics_ddl_preview():
    """CI review of schema. Does not execute SQL or enable network access."""
    return tuple(ddl for _,_,ddl in _DATA)


def inspect_business_analytics_sqlite(db):
    """Return only column/table counts and no stored facts, URLs or cursors."""
    if not isinstance(db,sqlite3.Connection):
        raise TypeError('Initialized offline SQLite connection required')
    items=[]
    for name,cols,_ in _DATA:
        actual=tuple(row[1] for row in db.execute(
            'PRAGMA table_info("'+name+'")'))
        if actual!=cols:
            raise ValueError('Source schema drift requires review: '+name)
        items.append({'table':name,'column_count':len(cols),
                      'rows':db.execute(
                          'SELECT COUNT(*) FROM "'+name+'"').fetchone()[0]})
    return {'status':'business_analytics_sql_review_only',
            'table_count':len(items),'tables':items,
            'source_rows_exported':False,
            'provider_access_enabled':False,
            'postgres_connection_attempted':False,
            'production_ready':False,'publishing_enabled':False}
