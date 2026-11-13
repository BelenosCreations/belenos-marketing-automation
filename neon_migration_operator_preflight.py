"""Metadata-only operator preflight for a future BAM SQLite -> PostgreSQL cutover.

No SQL is executed against PostgreSQL. This module cannot authorize or perform
a live migration. It deliberately exposes incomplete source mapping, schema
drift and missing recovery controls as blockers, not as success.
"""
import hashlib
import json
import re
import sqlite3

from neon_ephemeral_ci_migrations import _PLANS
from neon_integrity_preflight import inspect_offline_integrity
from neon_schema_inventory import (
    REVIEWED_PREVIEW_NAMES, inventory_sqlite_for_neon)

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_REQUIREMENTS = (
    "independently_reviewed_full_sqlite_table_and_data_mapping",
    "versioned_postgresql_schema_and_transactional_migration_runner",
    "least_privilege_postgresql_connection_and_maintenance_window",
    "verified_encrypted_offsite_backup_with_external_key_custody",
    "independent_restoration_and_cross_tenant_parity_acceptance",
    "tested_application_rollback_and_write_fencing",
    "operator_approval_and_rehearsed_cutover_runbook",
)


def inactive_pg_schema_manifest():
    """Return deterministic hashes, never SQL text or connection strings."""
    if tuple(v for v, _ in _PLANS) != tuple(range(1, len(_PLANS) + 1)):
        raise ValueError("PostgreSQL preview migration versions changed")
    if len(_PLANS) != 8 or len(REVIEWED_PREVIEW_NAMES) != 46:
        raise ValueError("Unexpected reviewed PostgreSQL preview inventory")
    phases = []
    for version, statements in _PLANS:
        if (not isinstance(statements, (list, tuple)) or not statements
                or any(type(s) is not str or not s.strip() for s in statements)):
            raise ValueError("Invalid immutable SQL preview phase")
        digest = hashlib.sha256(
            (";\n".join(statements)).encode("utf-8")).hexdigest()
        phases.append({"version": version, "statement_count": len(statements),
                       "sql_sha256": digest})
    fingerprint = hashlib.sha256(json.dumps(
        phases, sort_keys=True, separators=(",", ":")).encode("ascii")).hexdigest()
    return {
        "status": "offline_pg_preview_manifest",
        "fingerprint": fingerprint,
        "phases": phases,
        "reviewed_table_count": len(REVIEWED_PREVIEW_NAMES),
        "postgres_connection_attempted": False,
        "migration_executed": False,
        "production_approved": False,
    }


def inspect_inactive_migration_preflight(db, *, pinned_source_digest=None):
    """Check offline source without reading or returning records.

    Pinned digest is a previously operator-reviewed SQLite DDL fingerprint,
    not a token, password or backup ID. Matching it never authorizes cutover.
    """
    if not isinstance(db, sqlite3.Connection):
        raise TypeError("Only trusted offline SQLite is accepted")
    if pinned_source_digest is not None and (
            type(pinned_source_digest) is not str
            or _SHA.fullmatch(pinned_source_digest) is None):
        raise ValueError("Invalid pinned source schema digest")
    source = inventory_sqlite_for_neon(db)
    integrity = inspect_offline_integrity(db)
    pg = inactive_pg_schema_manifest()
    unresolved = []
    if integrity["migration_fixture_issues_found"]:
        unresolved.append("source_integrity_findings")
    if source["unreviewed_pg_preview_count"]:
        unresolved.append("unreviewed_source_tables")
    if source["reviewed_pg_preview_uninitialized_names"]:
        unresolved.append("reviewed_tables_not_initialized_in_source")
    if pinned_source_digest is None:
        unresolved.append("source_schema_fingerprint_not_pinned")
    elif pinned_source_digest != source["schema_digest"]:
        unresolved.append("pinned_source_schema_drift")
    # Even a healthy source and pinned preview do not establish the
    # existence of the independent production controls listed below.
    unresolved.extend(_REQUIREMENTS)
    return {
        "status": "offline_operator_preflight_blocked",
        "source_schema_sha256": source["schema_digest"],
        "source_schema_pinned": pinned_source_digest is not None,
        "pinned_schema_matches": (
            pinned_source_digest == source["schema_digest"]
            if pinned_source_digest is not None else False),
        "postgres_schema_preview_sha256": pg["fingerprint"],
        "preview_version_count": len(pg["phases"]),
        "preview_table_count": pg["reviewed_table_count"],
        "source_table_count": source["all_table_count"],
        "unreviewed_source_table_count": source["unreviewed_pg_preview_count"],
        "unreviewed_source_table_names": source["unreviewed_pg_preview_table_names"],
        "uninitialized_preview_table_names":
            source["reviewed_pg_preview_uninitialized_names"],
        "source_integrity_ok": (
            integrity["integrity_check_ok"]
            and integrity["issue_count_total"] == 0),
        "aggregate_integrity_issue_count": integrity["issue_count_total"],
        "blockers": unresolved,
        "cutover_permitted": False,
        "rollback_executable": False,
        "postgres_connection_attempted": False,
        "customer_records_exported": False,
        "production_ready": False,
        "publishing_enabled": False,
    }
