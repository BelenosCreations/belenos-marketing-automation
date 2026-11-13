"""Negative/replay tests for the inactive migration INTENT journal."""
import copy
import os
import sqlite3
import unittest
from unittest.mock import patch

from audience_observation_store import AudienceObservationStore
from bam_offline_gateway import BAMOfflineGateway
from neon_column_transform_review import compile_offline_column_transform_review
from neon_inactive_migration_plan import compile_inactive_migration_plan
from neon_disposable_migration_journal import (
    build_disposable_migration_intent_journal,
    inspect_disposable_migration_intent_journal,
)


class DisposableMigrationJournalTests(unittest.TestCase):
    def setUp(self):
        self.previous = os.environ.get("BAM_EPHEMERAL_PG_TEST")
        os.environ["BAM_EPHEMERAL_PG_TEST"] = "1"
        self.db = sqlite3.connect(":memory:")
        self.gateway = BAMOfflineGateway(self.db, enabled=False)
        self.audience = AudienceObservationStore(self.db)
        p = compile_inactive_migration_plan(self.db)
        m = compile_offline_column_transform_review(self.db)
        self.pins = dict(
            pinned_source_sha256=p["source_schema_sha256"],
            pinned_plan_sha256=p["plan_sha256"],
            pinned_mapping_sha256=m["mapping_sha256"],
        )
        self.operation = "a" * 32

    def tearDown(self):
        self.db.close()
        if self.previous is None:
            os.environ.pop("BAM_EPHEMERAL_PG_TEST", None)
        else:
            os.environ["BAM_EPHEMERAL_PG_TEST"] = self.previous

    def build(self, **changes):
        return build_disposable_migration_intent_journal(
            self.db, operation_id=self.operation, **{**self.pins, **changes})

    def inspect(self, journal, **changes):
        return inspect_disposable_migration_intent_journal(
            self.db, journal, independent_head_sha256=journal["head_sha256"],
            **{**self.pins, **changes})

    def test_metadata_bound_hash_chain_is_only_a_plan_not_an_execution(self):
        before = self.db.total_changes
        journal = self.build()
        report = self.inspect(journal)
        self.assertEqual(journal, self.build())
        self.assertEqual(len(journal["events"]), 7)
        self.assertEqual(report["last_proposed_stage"], "07")
        self.assertTrue(report["journal_chain_matches_external_head"])
        self.assertEqual(self.db.total_changes, before)
        for flag in ("customer_rows_read", "postgres_connected",
                     "transaction_executed", "application_write_fence_implemented",
                     "rollback_rehearsed", "promotion_stage_accepted",
                     "operator_approval_proven", "cutover_permitted",
                     "production_ready", "publishing_enabled"):
            self.assertFalse(report[flag], flag)

    def test_partial_intent_ok_but_promotion_and_skips_never_allowed(self):
        short = self.build(through_sequence=3)
        self.assertEqual(self.inspect(short)["proposed_stage_count"], 3)
        for stage in (0, 8, True, "7", -1):
            with self.subTest(stage=stage), self.assertRaises(PermissionError):
                self.build(through_sequence=stage)
        for changed in (
            lambda j: j["events"].reverse(),
            lambda j: j["events"].pop(0),
            lambda j: j["events"][1].update(intent="executed"),
            lambda j: j["events"][0].update(extra="unknown"),
            lambda j: j["events"][1].update(sequence="08"),
            lambda j: j.update(operation_id="b" * 32),
            lambda j: j.update(head_sha256="0" * 64),
        ):
            tampered = copy.deepcopy(self.build())
            changed(tampered)
            with self.assertRaises(PermissionError):
                self.inspect(tampered)

    def test_replay_in_other_operation_or_external_head_is_rejected(self):
        journal = self.build()
        other = self.build(operation_id="b" * 32)
        self.assertNotEqual(journal["head_sha256"], other["head_sha256"])
        with self.assertRaises(PermissionError):
            inspect_disposable_migration_intent_journal(
                self.db, journal, independent_head_sha256=other["head_sha256"],
                **self.pins)
        with self.assertRaises(PermissionError):
            self.inspect(journal, pinned_mapping_sha256="f" * 64)

    def test_metadata_drift_and_disabled_mode_fail_before_operation(self):
        self.db.execute("ALTER TABLE bam_identities ADD COLUMN unexpected TEXT")
        with self.assertRaises(PermissionError):
            self.build()
        os.environ.pop("BAM_EPHEMERAL_PG_TEST")
        with patch("neon_disposable_migration_journal.compile_inactive_migration_plan") as forbidden:
            with self.assertRaises(PermissionError):
                self.build()
            forbidden.assert_not_called()

    def test_invalid_envelope_and_restricted_identifiers(self):
        with self.assertRaises(ValueError):
            self.build(operation_id="not-an-id")
        journal = self.build()
        journal["unknown_field"] = 1
        with self.assertRaises(ValueError):
            self.inspect(journal)
        journal = self.build()
        journal["events"][0]["event_sha256"] = "0" * 64
        with self.assertRaises(PermissionError):
            self.inspect(journal)


if __name__ == "__main__":
    unittest.main()
