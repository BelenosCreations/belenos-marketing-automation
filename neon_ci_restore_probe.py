"""All-table logical COPY/restore rehearsal on disposable CI PostgreSQL ONLY.

This streams synthetic table contents through memory into a second schema,
verifies exact relational parity, and destroys that schema atomically. It is
not pg_dump, a retained encrypted/durable backup, a customer migration, a recovery
point guarantee, or approval to run production PostgreSQL.
"""
import os
import hashlib
from offline_encrypted_backup import seal_disposable_backup, open_disposable_backup

from neon_schema_inventory import REVIEWED_PREVIEW_NAMES
from neon_ephemeral_ci_migrations import _PLANS
from neon_authenticated_read_contract import prepare_session_draft_read

_SOURCE='bam_ci_integration'
_RESTORE='bam_ci_restore_probe'
_TABLES=REVIEWED_PREVIEW_NAMES+('bam_ci_migration_journal',)
_MAX_TABLE_BYTES=2*1024*1024
_SCHEMA_FINGERPRINT=hashlib.sha256(repr(tuple(
    (version,tuple(statements)) for version,statements in _PLANS
)).encode('utf-8')).hexdigest()


def _synthetic_encrypted_roundtrip(name,data,key):
    """In-memory per-table authenticated restore rehearsal; no archive retained."""
    fingerprint=hashlib.sha256(
        (_SCHEMA_FINGERPRINT+':'+name).encode('utf-8')).hexdigest()
    envelope=seal_disposable_backup(
        plaintext=b'BAM_CI_CSV:'+data,root_key=key,
        schema_fingerprint=fingerprint,now=1000)
    recovered=open_disposable_backup(
        envelope=envelope,root_key=key,
        expected_schema_fingerprint=fingerprint,now=1001)
    if not recovered.startswith(b'BAM_CI_CSV:'):
        raise PermissionError('Invalid authenticated disposable table marker')
    return recovered[len(b'BAM_CI_CSV:'):]



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






def _check_column_shapes(conn):
    """Fail on column reorder, type, nullability or untracked additions.

    This supplements, not replaces, row/constraint/semantic validation. No
    schema DDL, column names, customer data or credentials are returned.
    """
    query="""SELECT column_name,udt_name,is_nullable,is_identity,is_generated
        FROM information_schema.columns
        WHERE table_schema=%s AND table_name=%s
        ORDER BY ordinal_position"""
    for name in _TABLES:
        original=conn.execute(query,(_SOURCE,name)).fetchall()
        restored=conn.execute(query,(_RESTORE,name)).fetchall()
        if not original or original!=restored:
            raise ValueError('Disposable restore column schema mismatch')


def _check_relational_shapes(conn):
    """Fail closed on lost/changed PG constraints and indexes in the rehearsal.

    Compare schema-independent catalog attributes, including FK targets:
    references must remain within the corresponding disposable schema.
    Nothing from these private catalog rows enters the public receipt.
    """
    constraints="""SELECT c.conname, c.contype, c.conkey::text,
        c.confkey::text, c.confupdtype, c.confdeltype, c.confmatchtype,
        c.condeferrable, c.condeferred, c.convalidated,
        pg_get_expr(c.conbin,c.conrelid),
        CASE WHEN ref_ns.nspname=table_ns.nspname THEN 'same-schema'
             ELSE COALESCE(ref_ns.nspname,'') END,
        COALESCE(ref.relname,'')
      FROM pg_constraint c
      JOIN pg_class rel ON rel.oid=c.conrelid
      JOIN pg_namespace table_ns ON table_ns.oid=rel.relnamespace
      LEFT JOIN pg_class ref ON ref.oid=c.confrelid
      LEFT JOIN pg_namespace ref_ns ON ref_ns.oid=ref.relnamespace
      WHERE table_ns.nspname=%s AND rel.relname=%s
      ORDER BY c.conname"""
    indexes="""SELECT idx.relname, access.amname, i.indisunique,
        i.indisprimary, i.indisexclusion, i.indisvalid, i.indisready,
        i.indnkeyatts, i.indnatts, i.indkey::text, i.indoption::text,
        i.indcollation::text, i.indclass::text,
        pg_get_expr(i.indexprs,i.indrelid), pg_get_expr(i.indpred,i.indrelid)
      FROM pg_index i
      JOIN pg_class rel ON rel.oid=i.indrelid
      JOIN pg_namespace ns ON ns.oid=rel.relnamespace
      JOIN pg_class idx ON idx.oid=i.indexrelid
      JOIN pg_am access ON access.oid=idx.relam
      WHERE ns.nspname=%s AND rel.relname=%s
      ORDER BY idx.relname"""
    for name in _TABLES:
        for query in (constraints,indexes):
            source=conn.execute(query,(_SOURCE,name)).fetchall()
            restored=conn.execute(query,(_RESTORE,name)).fetchall()
            if source!=restored:
                raise ValueError('Disposable restore constraint or index shape mismatch')

def _prepare_restore_session_checks(session_probes):
    """Fixed-shape synthetic-only auth claims; raw bearers never returned."""
    if (type(session_probes) not in (tuple,list)
            or len(session_probes)>8):
        raise ValueError('At most eight synthetic restore checks required')
    checks=[]
    for item in session_probes:
        if (type(item) is not dict or set(item)!={
                'raw_session_token','tenant_id','request_id',
                'server_now','visible'} or type(item['visible']) is not bool):
            raise ValueError('Unexpected restore session check')
        query,params=prepare_session_draft_read(
            raw_session_token=item['raw_session_token'],
            tenant_id=item['tenant_id'],
            request_id=item['request_id'],
            server_now=item['server_now'])
        checks.append((query,params,item['visible']))
    return checks

def run_ephemeral_ci_logical_restore(conn,*,fail_mode=None,session_probes=()):
    """Round-trip all reviewed CI tables, preserving values and constraints.

    Data never leaves the same disposable local PostgreSQL instance.
    No backup file or provider credential is created.
    """
    _check_disposable_connection(conn)
    session_checks=_prepare_restore_session_checks(session_probes)
    if (fail_mode is not None and
            (type(fail_mode) is not str or fail_mode not in (
                'abort_after_copy','corrupt_restored_draft'))):
        raise ValueError('Unsupported disposable restore fault simulation')
    if len(_TABLES)!=47 or len(set(_TABLES))!=47:
        raise ValueError('Unexpected reviewed table count')
    with conn.transaction():
        # Keep every source export and final parity SELECT on one MVCC view.
        # A concurrent writer must not splice two points in time together.
        # DDL stays strictly in the disposable target schema.
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
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
        _check_column_shapes(conn)
        _check_relational_shapes(conn)
        # This single operator-policy row is seeded by the schema DDL.
        # Replace it with the exact source snapshot, never issue unpause.
        conn.execute('TRUNCATE '+_RESTORE+'.bam_ai_operator_control')
        # Per-table CI-only authenticated encrypt/decrypt before restore COPY.
        # No envelope, key or source bytes are retained outside this process.
        one_run_key=os.urandom(32)
        for number,name in enumerate(_TABLES):
            exported=_export_csv(conn,_SOURCE+'.'+name)
            restored=_synthetic_encrypted_roundtrip(name,exported,one_run_key)
            _import_csv(conn,_RESTORE+'.'+name,restored)
            if fail_mode=='abort_after_copy' and number==0:
                raise RuntimeError('Deliberately interrupted CI restore')
        if fail_mode=='corrupt_restored_draft':
            # Fault injection is confined to a disposable *target* schema.
            # The exact-parity verifier must reject this changed synthetic row.
            update=conn.execute("""UPDATE bam_ci_restore_probe.content_requests
                SET draft_text=draft_text||'[ci-corruption]'
                WHERE request_id=(
                    SELECT MIN(request_id)
                    FROM bam_ci_restore_probe.content_requests)""")
            if update.rowcount!=1:
                raise ValueError('No synthetic draft available for fault test')
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
        # Run restored data through real session-hash tenant-scoped SQL,
        # while search_path remains bound to the temporary restored schema.
        # This is a live-authorization regression, NOT a public token API.
        for sql,params,expected_visible in session_checks:
            records=conn.execute(sql,params).fetchmany(2)
            if len(records)>1 or bool(records)!=expected_visible:
                raise ValueError('Restored session/tenant privacy check failed')
        conn.execute('SET LOCAL search_path TO '+_SOURCE)
        conn.execute('DROP SCHEMA '+_RESTORE+' CASCADE')
    return {'status':'ephemeral_ci_logical_restore_verified',
            'reviewed_tables_rehearsed':len(_TABLES)-1,
            'consistent_source_snapshot_used':True,
            'column_shapes_checked':len(_TABLES),
            'constraint_and_index_shapes_checked':len(_TABLES),
            'migration_journal_rehearsed':True,
            'restored_session_checks_passed':len(session_checks),
            'separate_schema_discarded':True,
            'synthetic_ci_only':True,
             'ephemeral_encryption_roundtrips_checked':len(_TABLES),
             'encrypted_backup_retained':False,
            'backup_file_created':False,
            'customer_records_exported':False,
            'durable_backup_available':False,
            'production_restore_validated':False,
            'neon_connected':False,
            'publishing_enabled':False}
