"""Test-only, transactional/versioned schema loader for ephemeral CI Postgres.

Never invoke for Neon, production, customer data, or any public endpoint.
A separate reviewed production migration implementation is required.
Connection is restricted to the disposable GitHub CI database and schema.
"""
import hashlib
import os

from neon_schema_blueprint import TABLE_NAMES,ddl_preview
from neon_collaboration_schema import (
    COLLABORATION_NAMES,collaboration_ddl_preview)
from neon_identity_provider_schema import (
    EXTRA_TABLE_NAMES,identity_provider_ddl_preview)
from neon_ai_budget_schema import BUDGET_TABLE_NAMES,ai_budget_ddl_preview
from neon_business_analytics_schema import (BUSINESS_ANALYTICS_TABLES,
    business_analytics_ddl_preview)

_CI_SCHEMA='bam_ci_integration'
_PLANS=(
    (1,ddl_preview()),
    (2,collaboration_ddl_preview()),
    (3,identity_provider_ddl_preview()),
    (4,ai_budget_ddl_preview()),
    (5,business_analytics_ddl_preview()),
)
_JOURNAL='bam_ci_migration_journal'


def _checksum(statements):
    return hashlib.sha256((';\n'.join(statements)).encode('utf-8')).hexdigest()


def apply_ephemeral_ci_migrations(conn):
    """Use one atomic PG transaction + advisory lock for known synthetic DDL.

    No caller-supplied SQL, credentials, environment paths, or schema names.
    Unknown versions/checksum changes and missing expected tables fail closed.
    """
    if os.environ.get('BAM_EPHEMERAL_PG_TEST')!='1':
        raise PermissionError('Ephemeral CI migration only')
    import psycopg
    if not isinstance(conn,psycopg.Connection):
        raise TypeError('Psycopg connection required')
    info=conn.info
    if (info.host!='127.0.0.1' or info.dbname!='bam_ci_test'
            or info.user!='bam_ci' or int(info.port)!=5432
            or not conn.autocommit):
        raise PermissionError('Only local disposable CI PostgreSQL permitted')
    schema,dbname,user=conn.execute(
        'SELECT current_schema(),current_database(),current_user').fetchone()
    if (schema,dbname,user)!=(_CI_SCHEMA,'bam_ci_test','bam_ci'):
        raise PermissionError('Unexpected CI migration schema or database')
    expected={version:_checksum(sql) for version,sql in _PLANS}
    applied=[]
    with conn.transaction():
        # Lock scope is the disposable database (no production use).
        conn.execute('SELECT pg_advisory_xact_lock(%s)',(714094031,))
        conn.execute("""CREATE TABLE IF NOT EXISTS bam_ci_migration_journal (
            version INTEGER PRIMARY KEY,
            checksum TEXT NOT NULL,
            completed_at BIGINT NOT NULL)""")
        recorded=dict(conn.execute(
            'SELECT version,checksum FROM bam_ci_migration_journal').fetchall())
        for version,checksum in recorded.items():
            if expected.get(version)!=checksum:
                raise ValueError('Unrecognized or modified CI schema version')
        for version,statements in _PLANS:
            if version in recorded:
                continue
            for statement in statements:
                conn.execute(statement)
            conn.execute("""INSERT INTO bam_ci_migration_journal
                (version,checksum,completed_at) VALUES (%s,%s,0)""",
                (version,expected[version]))
            applied.append(version)
        names={row[0] for row in conn.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema=%s AND table_type='BASE TABLE'""",
            (_CI_SCHEMA,)).fetchall()}
        required=set(TABLE_NAMES+COLLABORATION_NAMES+EXTRA_TABLE_NAMES+
                     BUDGET_TABLE_NAMES+BUSINESS_ANALYTICS_TABLES+(_JOURNAL,))
        if names!=required:
            raise ValueError('Disposable PostgreSQL schema drift detected')
    return {'status':'ephemeral_ci_schema_verified',
            'versions_present':len(_PLANS),
            'versions_applied':applied,
            'migration_production_ready':False,
            'customer_records_migrated':False,
            'neon_connected':False,
            'social_publishing_enabled':False}
