"""Reviewed attachment-metadata schema for disposable BAM PostgreSQL CI.

This mirrors the existing offline registry's nine fields while tightening
cross-business ownership and metadata integrity. It stores only references:
NO file bytes, object storage, scanner, upload endpoint, public media URLs,
real credential access or publication permission.
"""
import sqlite3

MEDIA_TABLE_NAMES=("content_attachments",)

_DDL=(
    """CREATE UNIQUE INDEX content_requests_tenant_request_key
        ON content_requests(tenant_id,request_id)""",
    """CREATE TABLE content_attachments (
        attachment_id TEXT PRIMARY KEY
            CHECK(attachment_id ~ '^[0-9a-f]{32}$'),
        tenant_id TEXT NOT NULL,
        request_id TEXT NOT NULL,
        item TEXT NOT NULL,
        media_type TEXT NOT NULL CHECK(media_type IN
            ('image/jpeg','image/png','image/webp','video/mp4',
             'text/plain','application/pdf')),
        sha256 TEXT NOT NULL CHECK(sha256 ~ '^[0-9a-f]{64}$'),
        storage_key TEXT NOT NULL CHECK(length(storage_key)>0),
        status TEXT NOT NULL CHECK(status IN
            ('pending','verified','rejected')),
        created_at BIGINT NOT NULL CHECK(created_at>=0),
        UNIQUE(tenant_id,request_id,item,attachment_id),
        FOREIGN KEY(tenant_id,request_id)
            REFERENCES content_requests(tenant_id,request_id)
    )""",
    """CREATE INDEX content_attachments_private_state
        ON content_attachments(tenant_id,request_id,item,status)""",
)

_SOURCE_COLUMNS=(
    "attachment_id","tenant_id","request_id","item","media_type",
    "sha256","storage_key","status","created_at"
)


def media_ddl_preview():
    """DDL for ephemeral CI migrations only, not a production migration."""
    return _DDL


def inspect_media_sqlite(db):
    """Metadata-only source schema inspection, never private media fields."""
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
