"""Offline SQLite-to-PostgreSQL migration execution *planning* contract.

This intentionally cannot connect to PostgreSQL, copy customer records, apply
DDL, fence writers, change a live backend or approve a cutover. The reviewed
47-object CI restore path remains separate from production data mapping.
"""
import hashlib
import json
import re
import sqlite3

from neon_migration_operator_preflight import (
    inactive_pg_schema_manifest, inspect_inactive_migration_preflight)
from neon_schema_inventory import REVIEWED_PREVIEW_NAMES

_NAME = re.compile(r"[a-z][a-z0-9_]*\\Z")
_SHA = re.compile(r"[0-9a-f]{64}\\Z")
_OPERATOR_STEPS = (
    ("01", "review_independent_backup_and_external_key_recovery"),
    ("02", "obtain_maintenance_approval_and_fence_all_writers"),
    ("03", "verify_sqlite_snapshot_and_full_column_transform_map"),
    ("04", "apply_versioned_postgresql_schema_in_shadow_transaction"),
    ("05", "copy_approved_rows_with_scoped_identity_remapping"),
    ("06", "compare_row_fingerprints_constraints_and_tenant_access"),
    ("07", "rehearse_rollback_and_validate_restored_app_sessions"),
    ("08", "authorize_target_promotion_only_after_independent_signoff"),
)
_EXTRA_BLOCKERS = (
    "all_source_to_target_columns_and_data_transformations_not_reviewed",
    "operator_write_fencing_not_implemented",
    "customer_data_export_and_postgresql_runner_disabled",
    "production_application_rollback_not_rehearsed",
)


def _pin(value, label):
    if value is not None and (type(value) is not str
                              or _SHA.fullmatch(value) is None):
        raise ValueError("Invalid " + label + " SHA-256 pin")


def _column_inventory(db, name):
    if _NAME.fullmatch(name) is None:
        raise ValueError("Unsafe source table identifier")
    rows = db.execute('PRAGMA table_info("' + name + '")').fetchall()
    if not rows:
        raise ValueError("Source table has no visible columns")
    columns = []
    for cid, col, dtype, nonnull, default, pk in rows:
        if (type(col) is not str or _NAME.fullmatch(col) is None
                or type(dtype) is not str or len(dtype) > 64
                or type(cid) is not int or cid < 0):
            raise ValueError("Unreviewed source column metadata")
        # No default SQL expressions or values leave this function.
        columns.append({"ordinal": cid, "name": col,
                        "sqlite_declared_type": dtype.upper(),
                        "not_null": bool(nonnull), "pk_position": int(pk),
                        "has_default": default is not None})
    return columns


def compile_inactive_migration_plan(db, *, pinned_source_sha256=None,
                                    pinned_plan_sha256=None):
    """Return a deterministic source-side inventory and blocked operator plan.

    A matching independent pin is evidence of no observed metadata drift,
    NEVER approval to run this plan. Rows, defaults, SQL DDL and secrets are
    not returned. Empty optional source tables remain explicit blockers.
    """
    if not isinstance(db, sqlite3.Connection):
        raise TypeError("Only trusted offline SQLite connection is accepted")
    _pin(pinned_source_sha256, "source")
    _pin(pinned_plan_sha256, "plan")
    base = inspect_inactive_migration_preflight(
        db, pinned_source_digest=pinned_source_sha256)
    pg = inactive_pg_schema_manifest()
    source_names = {name for (name,) in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%'")}
    reviewed = set(REVIEWED_PREVIEW_NAMES)
    inventory = []
    for name in sorted(reviewed & source_names):
        inventory.append({"source_table": name, "target_table": name,
                          "source_columns": _column_inventory(db, name),
                          "target_columns_reviewed": False,
                          "row_transform_reviewed": False,
                          "tenant_boundary_reviewed": False})
    missing = sorted(reviewed - source_names)
    unreviewed = sorted(source_names - reviewed)
    stages = [{"sequence": seq, "required_action": action,
               "implemented": False, "executable": False}
              for seq, action in _OPERATOR_STEPS]
    shape = {"format": "bam-inactive-migration-plan-v1",
             "pg_schema_fingerprint": pg["fingerprint"],
             "pg_phases": pg["phases"], "tables": inventory,
             "missing_source_tables": missing,
             "unreviewed_source_tables": unreviewed,
             "operator_steps": stages}
    digest = hashlib.sha256(json.dumps(
        shape, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True).encode("ascii")).hexdigest()
    blockers = list(dict.fromkeys(base["blockers"] + list(_EXTRA_BLOCKERS)))
    if pinned_plan_sha256 is None:
        blockers.append("independently_pinned_execution_plan_missing")
    elif pinned_plan_sha256 != digest:
        blockers.append("independently_pinned_execution_plan_drift")
    if missing:
        blockers.append("uninitialized_source_tables")
    if unreviewed:
        blockers.append("unreviewed_source_tables")
    return {"status": "offline_migration_plan_blocked",
            "format": shape["format"], "plan_sha256": digest,
            "source_schema_sha256": base["source_schema_sha256"],
            "source_schema_pin_matches": base["pinned_schema_matches"],
            "plan_pin_matches": pinned_plan_sha256 == digest
            if pinned_plan_sha256 is not None else False,
            "postgres_schema_preview_sha256": pg["fingerprint"],
            "schema_phases": pg["phases"], "operator_steps": stages,
            "table_count": len(inventory), "source_table_mapping": inventory,
            "missing_source_tables": missing,
            "unreviewed_source_tables": unreviewed,
            "blockers": blockers, "cutover_permitted": False,
            "transactional_execution_implemented": False,
            "rollback_executable": False, "source_writes_performed": False,
            "rows_copied": False, "postgres_connected": False,
            "production_ready": False, "publishing_enabled": False}
