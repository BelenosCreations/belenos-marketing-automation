"""CI-only schema-semantic review; no customer values or migration execution.

The scanner reads only SQLite schema metadata and immutable PostgreSQL DDL
previews. Signals are conservative TODOs, NOT an accepted data mapping.
Matching external fingerprints never authorize transformations or promotion.
"""
import hashlib
import json
import os
import re
import sqlite3

from neon_column_transform_review import (
    _CATALOGS, compile_offline_column_transform_review,
)
from neon_migration_operator_preflight import inactive_pg_schema_manifest

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_COLUMN = re.compile(
    r"^([a-z][a-z0-9_]*)\s+"
    r"(?:TEXT|SMALLINT|INTEGER|BIGINT|BYTEA|DOUBLE\s+PRECISION)\b", re.I
)
_PK = re.compile(r"\bPRIMARY\s+KEY\s*\(([^)]*)\)", re.I)
_FK = re.compile(r"\bFOREIGN\s+KEY\s*\(([^)]*)\)", re.I)
_JSON_FIELDS = frozenset(("required_items", "provided_items", "manual_times"))


def _split_table_declarations(ddl):
    """Split outer CREATE TABLE clauses without splitting CHECK/quoted commas."""
    start = ddl.find("(")
    if start < 0 or not ddl.startswith("CREATE TABLE "):
        raise ValueError("Unexpected target schema preview")
    chunks = []
    depth = 0
    quote = False
    begin = start + 1
    index = start
    terminated = False
    while index < len(ddl):
        ch = ddl[index]
        if quote:
            if ch == "'":
                if index + 1 < len(ddl) and ddl[index + 1] == "'":
                    index += 2
                    continue
                quote = False
        elif ch == "'":
            quote = True
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                chunks.append(ddl[begin:index].strip())
                terminated = True
                break
            if depth < 0:
                raise ValueError("Unbalanced target declarations")
        elif ch == "," and depth == 1:
            chunks.append(ddl[begin:index].strip())
            begin = index + 1
        index += 1
    if not terminated or quote or not chunks or any(not part for part in chunks):
        raise ValueError("Invalid PostgreSQL table preview")
    return chunks


def _target_signals():
    targets = {}
    for group in _CATALOGS:
        for table, ordered_names, ddl in group:
            if table in targets:
                raise ValueError("Duplicate target table")
            columns = {}
            table_primary = set()
            table_foreign = set()
            table_checks = False
            for clause in _split_table_declarations(ddl):
                match = _COLUMN.match(clause)
                if match:
                    name = match.group(1)
                    if name in columns:
                        raise ValueError("Duplicate target column")
                    tail = clause[match.end():]
                    columns[name] = {
                        "explicit_not_null": bool(re.search(r"\bNOT\s+NULL\b", tail, re.I)),
                        "inline_primary_key": bool(re.search(r"\bPRIMARY\s+KEY\b", tail, re.I)),
                        "has_default": bool(re.search(r"\bDEFAULT\b", tail, re.I)),
                        "has_check": bool(re.search(r"\bCHECK\s*\(", tail, re.I)),
                        "has_inline_reference": bool(re.search(r"\bREFERENCES\b", tail, re.I)),
                    }
                else:
                    pk = _PK.search(clause)
                    fk = _FK.search(clause)
                    if pk:
                        table_primary.update(p.strip().lower() for p in pk.group(1).split(","))
                    if fk:
                        table_foreign.update(p.strip().lower() for p in fk.group(1).split(","))
                    if re.search(r"\bCHECK\s*\(", clause, re.I):
                        table_checks = True
                    if not (pk or fk or table_checks or
                            re.match(r"^CONSTRAINT\s+", clause, re.I) or
                            re.match(r"^UNIQUE\s*\(", clause, re.I)):
                        raise ValueError("Unknown target schema clause")
            if list(columns) != list(ordered_names):
                raise ValueError("Incomplete target schema semantic parsing")
            if (table_primary | table_foreign) - set(columns):
                raise ValueError("Unknown referenced target column")
            targets[table] = (columns, table_primary, table_foreign, table_checks)
    if len(targets) != 46:
        raise ValueError("Unexpected target-table inventory")
    return targets


def compile_disposable_semantic_review(
        db, *, pinned_source_sha256=None, pinned_mapping_sha256=None,
        pinned_preview_sha256=None, pinned_semantics_sha256=None):
    """Return independently pinnable but unapproved schema review signals."""
    if os.environ.get("BAM_EPHEMERAL_PG_TEST") != "1":
        raise PermissionError("CI-only semantic review must stay disabled")
    if not isinstance(db, sqlite3.Connection):
        raise TypeError("Explicit trusted disposable SQLite connection required")
    for name, pin in (
        ("source", pinned_source_sha256),
        ("mapping", pinned_mapping_sha256),
        ("preview", pinned_preview_sha256),
        ("semantics", pinned_semantics_sha256),
    ):
        if pin is not None and (type(pin) is not str or not _SHA.fullmatch(pin)):
            raise ValueError("Invalid independent " + name + " fingerprint")
    mapping = compile_offline_column_transform_review(
        db, pinned_source_sha256=pinned_source_sha256,
        pinned_mapping_sha256=pinned_mapping_sha256)
    preview = inactive_pg_schema_manifest()["fingerprint"]
    target = _target_signals()
    reviews = []
    for item in mapping["mappings"]:
        table = item["target_table"]
        columns, primary, foreign, checks = target[table]
        reviewed = []
        for col in item["columns"]:
            name = col["column"]
            target_col = columns[name]
            target_pk = target_col["inline_primary_key"] or name in primary
            target_nonnull = target_col["explicit_not_null"] or target_pk
            source_pk = bool(col["source_pk_position"])
            source_nonnull = col["source_not_null"]
            json_signal = (
                col["target_type"] == "TEXT"
                and (name.endswith("_json") or name in _JSON_FIELDS)
            )
            reviewed.append({
                "column": name,
                "source_column_missing": col["source_type"] is None,
                "source_declares_not_null": source_nonnull,
                "source_primary_key_position": col["source_pk_position"],
                "target_declares_or_implies_not_null": target_nonnull,
                "sqlite_primary_key_nullability_ambiguous":
                    source_pk and source_nonnull is False,
                "source_to_target_nonnull_risk":
                    target_nonnull and source_nonnull is False,
                "source_has_default": col["source_has_default"],
                "target_has_default": target_col["has_default"],
                "default_presence_differs":
                    col["source_has_default"] is not None
                    and col["source_has_default"] != target_col["has_default"],
                "json_text_semantics_review_required": json_signal,
                "tenant_or_reference_review_required":
                    name == "tenant_id" or name.endswith("_id")
                    or target_col["has_inline_reference"] or name in foreign,
                "target_constraint_review_required":
                    checks or target_col["has_check"] or target_pk
                    or target_col["has_inline_reference"] or name in foreign,
                "value_and_constraint_reviewed": False,
            })
        reviews.append({
            "table": table,
            "source_table_present": item["source_table_present"],
            "shape_mismatch": table in mapping["column_shape_mismatch_tables"],
            "generated_identity_reseed_review_required":
                item["identity_sequence_requires_reseed_review"],
            "table_semantics_reviewed": False,
            "columns": reviewed,
        })
    commitment = {
        "format": "bam-disposable-migration-semantics-v1",
        "source_schema_sha256": mapping["source_schema_sha256"],
        "mapping_sha256": mapping["mapping_sha256"],
        "preview_sha256": preview,
        "tables": reviews,
    }
    digest = hashlib.sha256(json.dumps(
        commitment, sort_keys=True, ensure_ascii=True, separators=(",", ":")
    ).encode("ascii")).hexdigest()
    matches = {
        "source": pinned_source_sha256 == mapping["source_schema_sha256"]
                  if pinned_source_sha256 is not None else False,
        "mapping": pinned_mapping_sha256 == mapping["mapping_sha256"]
                   if pinned_mapping_sha256 is not None else False,
        "preview": pinned_preview_sha256 == preview
                   if pinned_preview_sha256 is not None else False,
        "semantics": pinned_semantics_sha256 == digest
                     if pinned_semantics_sha256 is not None else False,
    }
    blockers = [
        "all_column_nullability_default_json_constraint_reviews_unapproved",
        "identity_reseed_and_tenant_foreign_key_review_unapproved",
        "operator_authorization_write_fence_backup_rollback_unimplemented",
        "customer_data_migration_and_postgresql_promotion_disabled",
    ]
    blockers.extend("independent_" + name + "_pin_missing_or_drift"
                    for name, match in matches.items() if not match)
    if mapping["column_shape_mismatch_tables"]:
        blockers.append("source_target_column_shape_mismatch")
    return {
        "status": "offline_semantics_review_blocked",
        "format": commitment["format"],
        "source_schema_sha256": mapping["source_schema_sha256"],
        "mapping_sha256": mapping["mapping_sha256"],
        "preview_sha256": preview,
        "semantics_sha256": digest,
        "independent_pin_matches": matches,
        "table_count": len(reviews),
        "column_count": sum(len(row["columns"]) for row in reviews),
        "tables": reviews,
        "blockers": blockers,
        "all_semantics_approved": False,
        "customer_rows_read": False, "raw_default_expressions_returned": False,
        "postgres_connected": False, "source_writes_performed": False,
        "write_fence_implemented": False, "rollback_executable": False,
        "cutover_permitted": False, "production_ready": False,
        "publishing_enabled": False,
    }
