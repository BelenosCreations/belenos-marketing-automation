"""All-table logical COPY/restore rehearsal on disposable CI PostgreSQL ONLY.

This streams synthetic table contents through memory into a second schema,
verifies exact relational parity, and destroys that schema atomically. It is
not pg_dump, an encrypted/durable backup, a customer migration, a recovery
point guarantee, or approval to run production PostgreSQL.
"""
import os

from neon_schema_inventory import REVIEWED_PREVIEW_NAMES
from neon_ephemeral_ci_migrations import _PLANS

_SOURCE='bam_ci_integration'
_RESTORE='bam_ci_restore_probe'
_TABLES=REVIEWED_PREVIEW_NAMES+('bam_ci_migration_journal',)
_MAX_TABLE_BYTES=2*1024*1024


def _check_disposable_connection(conn):
    if os.environ.get('BAM_EPHEMERAL_PG_TEST')!='1':
        raise PermissionError('Disposable GitHub CI PostgreSQL only')
    import psycopg
    if not isinstance(conn,psycopg.Connection):
        raise TypeError('Psycopg CI connection required')
    info=conn.info
    if (info.host!='127.0.0.1' or int(info.port)!=5432
            or info.dbname!='bam_ci_test' or info.user!='bam_ci'
            or not conn.autocommit):
        raise PermissionError('Unknown database connection')
    observed=conn.execute(
        'SELECT current_schema(),current_database(),current_user').fetchone()
    if observed!=(_SOURCE,'bam_ci_test','bam_ci'):
        raise PermissionError('Unexpected disposable schema')


def _export_csv(conn,table):
    """Only pre-reviewed static identifiers, bounded synthetic test bytes."""
    data=bytearray()
    with conn.cursor() as cur:
        with cur.copy('COPY '+table+' TO STDOUT WITH (FORMAT CSV)') as copier:
            while True:
                chunk=copier.read()
                if not chunk:
                    break
                data.extend(chunk)
                if len(data)>_MAX_TABLE_BYTES:
                    raise ValueError('Synthetic table exceeds CI rehearsal cap')
    return bytes(data)


def _import_csv(conn,table,data):
    if type(data) is not bytes or len(data)>_MAX_TABLE_BYTES:
        raise ValueError('Invalid disposable restore payload')
    with conn.cursor() as cur:
        with cur.copy('COPY '+table+' FROM STDIN WITH (FORMAT CSV)') as copier:
            if data:
                copier.write(data)


def run_ephemeral_ci_logical_restore(conn):
    """Round-trip all reviewed CI tables, preserving values and constraints.

    Data never leaves the same disposable local PostgreSQL instance.
    No backup file or provider credential is created.
    """
    _check_disposable_connection(conn)
    if len(_TABLES)!=47 or len(set(_TABLES))!=47:
        raise ValueError('Unexpected reviewed table count')
    with conn.transaction():
        # Deterministic schema name, transactional DDL and rollback-on-error.
        # A leftover probe schema must fail, never overwrite prior data.
        conn.execute('CREATE SCHEMA '+_RESTORE)
        conn.execute('SET LOCAL search_path TO '+_RESTORE)
        for _,statements in _PLANS:
            for statement in statements:
                conn.execute(statement)
        conn.execute("""CREATE TABLE bam_ci_migration_journal (
            version INTEGER PRIMARY KEY,
            checksum TEXT NOT NULL,
            completed_at BIGINT NOT NULL)""")
        # This single operator-policy row is seeded by the schema DDL.
        # Replace it with the exact source snapshot, never issue unpause.
        conn.execute('TRUNCATE '+_RESTORE+'.bam_ai_operator_control')
        for name in _TABLES:
            _import_csv(conn,_RESTORE+'.'+name,
                        _export_csv(conn,_SOURCE+'.'+name))
        for name in _TABLES:
            old=_SOURCE+'.'+name
            new=_RESTORE+'.'+name
            # EXCEPT ALL detects missing, changed and duplicated rows,
            # including cross-tenant rows, without exposing any row values.
            missing=conn.execute('SELECT COUNT(*) FROM '
                '(SELECT * FROM '+old+' EXCEPT ALL '
                ' SELECT * FROM '+new+') AS delta').fetchone()[0]
            extra=conn.execute('SELECT COUNT(*) FROM '
                '(SELECT * FROM '+new+' EXCEPT ALL '
                ' SELECT * FROM '+old+') AS delta').fetchone()[0]
            if missing!=0 or extra!=0:
                raise ValueError('Disposable logical restore parity failed')
        conn.execute('SET LOCAL search_path TO '+_SOURCE)
        conn.execute('DROP SCHEMA '+_RESTORE+' CASCADE')
    return {'status':'ephemeral_ci_logical_restore_verified',
            'reviewed_tables_rehearsed':len(_TABLES)-1,
            'migration_journal_rehearsed':True,
            'separate_schema_discarded':True,
            'synthetic_ci_only':True,
            'backup_file_created':False,
            'customer_records_exported':False,
            'durable_backup_available':False,
            'production_restore_validated':False,
            'neon_connected':False,
            'publishing_enabled':False}
