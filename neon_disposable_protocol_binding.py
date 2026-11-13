"""CI-only pinned intent/semantic binding for a disposable transaction rehearsal.

No production data moves. Caller-supplied independent pins are checked against
the actual *offline* source schema, intent journal, target preview and semantic
review. Matching hashes do not authenticate a person, custody or approval.
"""
import os
import sqlite3

from neon_disposable_column_semantics import compile_disposable_semantic_review
from neon_disposable_migration_journal import (
    inspect_disposable_migration_intent_journal,
)
from neon_disposable_versioned_protocol import (
    rehearse_disposable_versioned_protocol,
)


def rehearse_pinned_disposable_protocol(
        db, *, journal, independent_journal_head_sha256,
        pinned_source_sha256, pinned_plan_sha256, pinned_mapping_sha256,
        pinned_preview_sha256, pinned_semantics_sha256,
        fence_token, epoch, release_mode="rollback"):
    """Validate an unapproved, fully proposed journal before synthetic steps."""
    if os.environ.get("BAM_EPHEMERAL_PG_TEST") != "1":
        raise PermissionError("Offline pinned protocol binding disabled")
    if not isinstance(db, sqlite3.Connection):
        raise TypeError("Explicit offline SQLite fixture connection required")

    original_changes = db.total_changes
    inspection = inspect_disposable_migration_intent_journal(
        db, journal, independent_head_sha256=independent_journal_head_sha256,
        pinned_source_sha256=pinned_source_sha256,
        pinned_plan_sha256=pinned_plan_sha256,
        pinned_mapping_sha256=pinned_mapping_sha256)
    if (inspection["proposed_stage_count"] != 7 or
            inspection["last_proposed_stage"] != "07"):
        raise PermissionError("Only a complete unexecuted intent 01..07 is accepted")

    semantics = compile_disposable_semantic_review(
        db, pinned_source_sha256=pinned_source_sha256,
        pinned_mapping_sha256=pinned_mapping_sha256,
        pinned_preview_sha256=pinned_preview_sha256,
        pinned_semantics_sha256=pinned_semantics_sha256)
    if not all(semantics["independent_pin_matches"].values()):
        raise PermissionError("Pinned schema/preview/semantic review drift")
    if db.total_changes != original_changes:
        raise AssertionError("Read-only metadata inspection mutated SQLite source")

    # Intent-head equality is checked by the existing journal validator;
    # the disposable protocol receives the same ID/head as immutable context.
    simulated = rehearse_disposable_versioned_protocol(
        operation_id=journal["operation_id"],
        journal_head=independent_journal_head_sha256,
        fence_token=fence_token, epoch=epoch, release_mode=release_mode)
    if db.total_changes != original_changes:
        raise AssertionError("Synthetic protocol changed source fixture")
    return {
        **simulated,
        "status": "ci_only_pinned_intent_protocol_rehearsed_unapproved",
        "metadata_source_mapping_plan_pins_match": True,
        "external_intent_head_matches_hash_chain": True,
        "preview_and_semantic_fingerprints_match": True,
        "intent_stages": inspection["proposed_stage_count"],
        "unreviewed_semantic_column_signals": semantics["column_count"],
        "semantic_transforms_approved": False,
        "source_data_rows_read": False,
        "source_fixture_writes_performed": False,
        "external_pin_custody_proven": False,
        "journal_signatures_authenticated": False,
        "independent_operator_authorization_proven": False,
        "persistent_replay_authority_implemented": False,
        "production_ready": False,
        "cutover_permitted": False,
    }
