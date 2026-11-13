"""CI-only strict candidate SQLite -> PostgreSQL typed-value acceptance.

Takes explicit synthetic cell values, never queries source table rows, never
builds SQL or connects to Postgres. An independently pinned *proposal* and a
passed synthetic cell test NEVER approve customer transformations or cutover.
All outputs contain only bounded public schema identifiers and digests.
"""
import hashlib
import hmac
import math
import os
import sqlite3
import struct

from neon_column_transform_review import compile_offline_column_transform_review

_MAX_SYNTHETIC = 4096
_INT_LIMITS = {
    "SMALLINT": (-(2 ** 15), 2 ** 15 - 1),
    "INTEGER": (-(2 ** 31), 2 ** 31 - 1),
    "BIGINT": (-(2 ** 63), 2 ** 63 - 1),
}
_ALLOWED_PROPOSALS = {
    "text_encoding_collation_json_and_semantics_review",
    "integer_range_null_boolean_and_constraint_review",
    "finite_floating_point_precision_and_null_review",
    "blob_to_bytea_binary_adapter_review",
}


def _canonical_synthetic_cell(value, source_type, target_type):
    """Strict type and range checks, with unambiguous canonical test bytes.

    NULL and semantic coercions are intentionally not supported; source/PG
    constraints and optionality require independent table-specific review.
    """
    if value is None:
        raise ValueError("Nullability needs independent target review")
    if source_type == "TEXT" and target_type == "TEXT":
        if type(value) is not str or "\x00" in value:
            raise ValueError("Unsafe TEXT candidate value")
        try:
            encoded = value.encode("utf-8", "strict")
        except UnicodeError as exc:
            raise ValueError("Invalid Unicode for PostgreSQL text") from exc
        if len(encoded) > _MAX_SYNTHETIC:
            raise ValueError("Oversized synthetic text")
        return b"T" + encoded
    if source_type == "INTEGER" and target_type in _INT_LIMITS:
        if type(value) is not int:
            raise ValueError("Integer target cannot silently coerce data")
        low, high = _INT_LIMITS[target_type]
        if not low <= value <= high:
            raise ValueError("PostgreSQL target integer range exceeded")
        return b"I" + str(value).encode("ascii")
    if source_type == "REAL" and target_type == "DOUBLE PRECISION":
        if type(value) is not float or not math.isfinite(value):
            raise ValueError("Floating target must be a finite float")
        return b"F" + struct.pack(">d", value)
    if source_type == "BLOB" and target_type == "BYTEA":
        if type(value) is not bytes or len(value) > _MAX_SYNTHETIC:
            raise ValueError("Invalid bounded synthetic BYTEA")
        return b"B" + value
    raise PermissionError("Unreviewed type pairing cannot be transformed")


def inspect_disposable_typed_cell(*, db, table, column, value,
                                  pinned_source_sha256,
                                  pinned_mapping_sha256):
    """Inspect one synthetic candidate without returning its original value.

    External source and mapping pins MUST be independently provided. Even
    correctly matched pins and accepted canaries are not operator approval.
    """
    if os.environ.get("BAM_EPHEMERAL_PG_TEST") != "1":
        raise PermissionError("CI-only synthetic type acceptance")
    if not isinstance(db, sqlite3.Connection):
        raise TypeError("Trusted offline SQLite fixture required")
    report = compile_offline_column_transform_review(
        db, pinned_source_sha256=pinned_source_sha256,
        pinned_mapping_sha256=pinned_mapping_sha256)
    if not report["source_pin_matches"] or not report["mapping_pin_matches"]:
        raise PermissionError("Independent source/mapping pin mismatch")
    if type(table) is not str or type(column) is not str:
        raise ValueError("Exact target table and column required")
    matches = [item for item in report["mappings"] if item["target_table"] == table]
    if len(matches) != 1:
        raise ValueError("Unknown target table")
    entry = matches[0]
    if (not entry["source_table_present"]
            or entry["source_only_columns"]
            or table in report["column_shape_mismatch_tables"]):
        raise PermissionError("Source/target table shape requires review")
    columns = [col for col in entry["columns"] if col["column"] == column]
    if len(columns) != 1:
        raise ValueError("Unknown target column")
    item = columns[0]
    if item["candidate_conversion"] not in _ALLOWED_PROPOSALS:
        raise PermissionError("Unreviewed type pairing cannot be inspected")
    canonical = _canonical_synthetic_cell(
        value, item["source_type"], item["target_type"])
    payload = b"bam-synthetic-cell-v1\x00" + (
        table + "." + column + "\x00").encode("ascii") + canonical
    commitment = hashlib.sha256(payload).hexdigest()
    return {
        "status": "disposable_typed_cell_candidate_checked",
        "table": table, "column": column,
        "source_type": item["source_type"], "target_type": item["target_type"],
        "synthetic_cell_sha256": commitment,
        "source_schema_pin_matches": True, "mapping_pin_matches": True,
        "raw_value_returned": False, "customer_records_read": False,
        "postgres_connected": False, "source_writes_performed": False,
        "row_transform_approved": False, "target_constraints_approved": False,
        "tenant_relationships_approved": False, "production_ready": False,
        "migration_executable": False, "publishing_enabled": False,
    }
