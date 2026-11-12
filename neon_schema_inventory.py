"""Private metadata-only inventory for BAM's incomplete Neon port.

This module reads local SQLite DDL metadata, never customer rows, credentials
or files. A complete count of legacy tables does not imply PostgreSQL
compatibility; no driver, network, migration or deploy capability is present.
"""
import hashlib
import json
import re
import sqlite3

from neon_schema_blueprint import TABLE_NAMES

_SAFE_TABLE = re.compile(r'[a-z][a-z0-9_]*\Z')
_SIGNALS = (
    ('sqlite_autoincrement','AUTOINCREMENT'),
    ('binary_blob_conversion','BLOB'),
    ('foreign_key_review','REFERENCES'),
    ('constraint_semantics_review','CHECK'),
)


def inventory_sqlite_for_neon(db):
    """Report DDL shape only; never include SQL text, row data or values."""
    if not isinstance(db,sqlite3.Connection):
        raise TypeError('Local SQLite connection required')
    rows=db.execute("""SELECT name,sql FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name""").fetchall()
    if not rows:
        raise ValueError('Initialized BAM schema required')
    entries=[]
    shape=[]
    for name,ddl in rows:
        if (type(name) is not str or _SAFE_TABLE.fullmatch(name) is None
                or type(ddl) is not str or not ddl.strip()):
            raise ValueError('Unexpected local database schema identifier')
        # This identifier is first validated as a strict unquoted SQL name.
        columns=db.execute('PRAGMA table_info("'+name+'")').fetchall()
        if not columns:
            raise ValueError('Empty local table schema')
        indexed=db.execute('PRAGMA index_list("'+name+'")').fetchall()
        foreign=db.execute('PRAGMA foreign_key_list("'+name+'")').fetchall()
        types=[c[2].upper() for c in columns]
        markers=[label for label,text in _SIGNALS
                 if text in ddl.upper()]
        if any('TEXT'==t for t in types):
            markers.append('text_columns_require_semantic_review')
        shape.append([name,ddl])
        entries.append({
            'table':name,'mapped_in_initial_subset':name in TABLE_NAMES,
            'column_count':len(columns),'index_count':len(indexed),
            'foreign_key_count':len(foreign),
            'review_signals':sorted(markers)
        })
    names={entry['table'] for entry in entries}
    if not names.issuperset(TABLE_NAMES):
        raise ValueError('Core BAM identity/draft tables missing')
    missing=sorted(names-set(TABLE_NAMES))
    digest=hashlib.sha256(json.dumps(shape,
        separators=(',',':')).encode('utf-8')).hexdigest()
    return {'status':'sqlite_schema_inventory_only',
            'target':'separate_neon_free_postgresql',
            'all_table_count':len(entries),
            'mapped_subset_count':len(TABLE_NAMES),
            'unmapped_table_count':len(missing),
            'unmapped_table_names':missing,
            'schema_digest':digest,
            'tables':entries,
            'contains_customer_records':False,
            'contains_raw_schema_ddl':False,
            'provider_connected':False,
            'migration_executed':False,
            'ready_for_hosting':False,
            'posting_enabled':False}


def inventory_fresh_offline_gateway():
    """Developer CI command: instantiate only ephemeral in-memory schema."""
    from bam_offline_gateway import BAMOfflineGateway
    db=sqlite3.connect(':memory:')
    try:
        BAMOfflineGateway(db,enabled=False)
        return inventory_sqlite_for_neon(db)
    finally:
        db.close()


if __name__=='__main__':
    print(json.dumps(inventory_fresh_offline_gateway(),
                     sort_keys=True,indent=2))
