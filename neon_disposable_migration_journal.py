"""CI-only hash-chained migration INTENT journal, never an execution record.

A caller-supplied independent journal-head pin detects accidental or adversarial
drift only when the pin is actually held independently. SHA-256 is not a
signature; this module makes no claim about operator identity or approvals.
Nothing here opens PostgreSQL, performs writes or authorizes stage 08.
"""
import hashlib
import hmac
import json
import os
import re
import sqlite3

from neon_column_transform_review import compile_offline_column_transform_review
from neon_inactive_migration_plan import (
    _OPERATOR_STEPS, compile_inactive_migration_plan,
)

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_OPERATION = re.compile(r"[0-9a-f]{32}\Z")
_FORMAT = "bam-disposable-migration-intent-journal-v1"
_EVENT_FIELDS = frozenset((
    "sequence", "required_action", "intent", "previous_head_sha256",
    "event_sha256",
))
_TOP_FIELDS = frozenset((
    "format", "operation_id", "source_schema_sha256", "plan_sha256",
    "mapping_sha256", "events", "head_sha256",
))
_GENESIS = "0" * 64


def _digest(obj):
    return hashlib.sha256(json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")).hexdigest()


def _pin(value, name):
    if type(value) is not str or _SHA.fullmatch(value) is None:
        raise ValueError("Exact external " + name + " SHA-256 required")


def _metadata_pins(db, source, plan, mapping):
    if os.environ.get("BAM_EPHEMERAL_PG_TEST") != "1":
        raise PermissionError("Offline CI-only intent journal")
    if not isinstance(db, sqlite3.Connection):
        raise TypeError("Only an explicitly supplied SQLite fixture is accepted")
    for name, pin in (("source", source), ("plan", plan), ("mapping", mapping)):
        _pin(pin, name)
    plan_report = compile_inactive_migration_plan(
        db, pinned_source_sha256=source, pinned_plan_sha256=plan)
    mapping_report = compile_offline_column_transform_review(
        db, pinned_source_sha256=source, pinned_mapping_sha256=mapping)
    if (not plan_report["source_schema_pin_matches"]
            or not plan_report["plan_pin_matches"]
            or not mapping_report["source_pin_matches"]
            or not mapping_report["mapping_pin_matches"]):
        raise PermissionError("Source/plan/mapping drift; no journal accepted")


def _candidate_event(sequence, previous):
    stage, action = _OPERATOR_STEPS[sequence - 1]
    record = {
        "sequence": stage, "required_action": action,
        "intent": "not_executed", "previous_head_sha256": previous,
    }
    record["event_sha256"] = _digest(record)
    return record


def build_disposable_migration_intent_journal(
        db, *, operation_id, pinned_source_sha256, pinned_plan_sha256,
        pinned_mapping_sha256, through_sequence=7):
    """Produce deterministic *proposed* steps 01..07, with no side effects."""
    _metadata_pins(db, pinned_source_sha256, pinned_plan_sha256,
                   pinned_mapping_sha256)
    if type(operation_id) is not str or _OPERATION.fullmatch(operation_id) is None:
        raise ValueError("External opaque 128-bit operation ID required")
    if type(through_sequence) is not int or not 1 <= through_sequence <= 7:
        raise PermissionError("Only pre-promotion intent stages 01..07 permitted")
    header = {
        "format": _FORMAT, "operation_id": operation_id,
        "source_schema_sha256": pinned_source_sha256,
        "plan_sha256": pinned_plan_sha256,
        "mapping_sha256": pinned_mapping_sha256,
    }
    # The operation/pin binding is in the genesis, so a trace from another
    # operation cannot be replayed with a fresh ID or altered schema pins.
    previous = _digest(header)
    events = []
    for number in range(1, through_sequence + 1):
        record = _candidate_event(number, previous)
        events.append(record)
        previous = record["event_sha256"]
    return {**header, "events": events, "head_sha256": previous}


def inspect_disposable_migration_intent_journal(
        db, journal, *, independent_head_sha256,
        pinned_source_sha256, pinned_plan_sha256, pinned_mapping_sha256):
    """Recheck exact pin-bound chain; never treat it as authenticated approval."""
    _metadata_pins(db, pinned_source_sha256, pinned_plan_sha256,
                   pinned_mapping_sha256)
    _pin(independent_head_sha256, "journal head")
    if type(journal) is not dict or set(journal) != _TOP_FIELDS:
        raise ValueError("Unrecognized migration journal envelope")
    operation = journal["operation_id"]
    if type(operation) is not str or _OPERATION.fullmatch(operation) is None:
        raise ValueError("Invalid operation identifier")
    header = {
        "format": _FORMAT, "operation_id": operation,
        "source_schema_sha256": pinned_source_sha256,
        "plan_sha256": pinned_plan_sha256,
        "mapping_sha256": pinned_mapping_sha256,
    }
    for field, value in header.items():
        if journal[field] != value or type(journal[field]) is not str:
            raise PermissionError("Journal context or source pin replay/drift")
    events = journal["events"]
    if type(events) is not list or not 1 <= len(events) <= 7:
        raise PermissionError("Missing, excessive, or promotion-stage journal")
    previous = _digest(header)
    for number, provided in enumerate(events, 1):
        if type(provided) is not dict or set(provided) != _EVENT_FIELDS:
            raise PermissionError("Unknown or incomplete intent record")
        expected = _candidate_event(number, previous)
        if provided != expected:
            raise PermissionError("Reordered, altered or replayed journal record")
        previous = expected["event_sha256"]
    if (type(journal["head_sha256"]) is not str
            or not hmac.compare_digest(previous, journal["head_sha256"])
            or not hmac.compare_digest(previous, independent_head_sha256)):
        raise PermissionError("External journal head mismatch")
    return {
        "status": "offline_migration_intent_chain_checked_unapproved",
        "format": _FORMAT, "operation_id": operation,
        "proposed_stage_count": len(events),
        "last_proposed_stage": events[-1]["sequence"],
        "journal_chain_matches_external_head": True,
        "source_plan_mapping_pins_match": True,
        "source_metadata_only": True, "customer_rows_read": False,
        "postgres_connected": False, "transaction_executed": False,
        "application_write_fence_implemented": False,
        "backup_authority_verified": False,
        "independent_reviewers_authenticated": False,
        "rollback_rehearsed": False, "rollback_executable": False,
        "promotion_stage_accepted": False, "operator_approval_proven": False,
        "cutover_permitted": False, "production_ready": False,
        "publishing_enabled": False,
    }
