"""Eighth, constraint-only hardening stage for existing attachment metadata.

'content_attachments' is already created in the version-3 identity/provider
preview. This stage adds constraints and a tenant/request foreign key to that
existing table; it MUST NOT create or recount the table. Disposable CI only:
no actual media bytes, scanner, upload, storage or production migration.
"""
import sqlite3

# Stage 8 intentionally defines NO new tables. Preserve stage 3 checksum.
MEDIA_TABLE_NAMES=()
MEDIA_HARDENED_TABLES=("content_attachments",)

_DDL=(
    """CREATE UNIQUE INDEX content_requests_tenant_request_key
        ON content_requests(tenant_id,request_id)""",
    """ALTER TABLE content_attachments
        ADD CONSTRAINT content_attachments_tenant_request_fkey
        FOREIGN KEY(tenant_id,request_id)
        REFERENCES content_requests(tenant_id,request_id)""",
    """ALTER TABLE content_attachments
        ADD CONSTRAINT content_attachments_id_shape
        CHECK(attachment_id ~ '^[0-9a-f]{32}$')""",
    """ALTER TABLE content_attachments
        ADD CONSTRAINT content_attachments_item_shape
        CHECK(item ~ '^[a-z][a-z0-9_-]{0,63}$')""",
    """ALTER TABLE content_attachments
        ADD CONSTRAINT content_attachments_media_type_check
        CHECK(media_type IN
            ('image/jpeg','image/png','image/webp','video/mp4',
             'text/plain','application/pdf'))""",
    """ALTER TABLE content_attachments
        ADD CONSTRAINT content_attachments_sha256_shape
        CHECK(sha256 ~ '^[0-9a-f]{64}$')""",
    """ALTER TABLE content_attachments
        ADD CONSTRAINT content_attachments_private_key_check
        CHECK(length(storage_key)>0)""",
    """ALTER TABLE content_attachments
        ADD CONSTRAINT content_attachments_timestamp_check
        CHECK(created_at>=0)""",
    """CREATE INDEX content_attachments_private_state
        ON content_attachments(tenant_id,request_id,item,status)""",
)

_SOURCE_COLUMNS=(
    "attachment_id","tenant_id","request_id","item","media_type",
    "sha256","storage_key","status","created_at"
)


def media_ddl_preview():
    """Constraint-only statements; stage 3 creates the existing table."""
    return _DDL


def inspect_media_sqlite(db):
    """Metadata-only source inspection, never private media fields."""
    if not isinstance(db,sqlite3.Connection):
        raise TypeError("Trusted offline SQLite required")
    actual=tuple(row[1] for row in db.execute(
        'PRAGMA table_info("content_attachments")'))
    if actual!=_SOURCE_COLUMNS:
        raise ValueError("Attachment registry schema needs manual review")
    rows=db.execute(
        'SELECT COUNT(*) FROM "content_attachments"').fetchone()[0]
    if type(rows) is not int or rows<0:
        raise ValueError("Unexpected attachment count")
    return {"status":"media_metadata_schema_preview_only",
            "table_count":1,"columns":len(actual),"rows":rows,
            "media_bytes_read":False,"storage_keys_exported":False,
            "customer_records_exported":False,
            "real_scanning_enabled":False,"media_verified_by_preview":False,
            "production_ready":False,"publishing_enabled":False}
