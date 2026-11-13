"""Cross-module, hostile synthetic binding tests for inactive migration v1."""
import copy
import os
import sqlite3
import unittest
from unittest.mock import patch

from audience_observation_store import AudienceObservationStore
from bam_offline_gateway import BAMOfflineGateway
from neon_column_transform_review import compile_offline_column_transform_review
from neon_disposable_column_semantics import compile_disposable_semantic_review
from neon_disposable_migration_journal import (
    build_disposable_migration_intent_journal,
)
from neon_disposable_protocol_binding import rehearse_pinned_disposable_protocol
from neon_inactive_migration_plan import compile_inactive_migration_plan


class DisposableProtocolBindingTests(unittest.TestCase):
    def setUp(self):
        self.old = os.environ.get("BAM_EPHEMERAL_PG_TEST")
        os.environ["BAM_EPHEMERAL_PG_TEST"] = "1"
        self.db = sqlite3.connect(":memory:")
        self.gateway = BAMOfflineGateway(self.db, enabled=False)
        self.audience = AudienceObservationStore(self.db)
        plan = compile_inactive_migration_plan(self.db)
        mapping = compile_offline_column_transform_review(self.db)
        semantics = compile_disposable_semantic_review(self.db)
        self.pins = dict(
            pinned_source_sha256=plan["source_schema_sha256"],
            pinned_plan_sha256=plan["plan_sha256"],
            pinned_mapping_sha256=mapping["mapping_sha256"],
            pinned_preview_sha256=semantics["preview_sha256"],
            pinned_semantics_sha256=semantics["semantics_sha256"],
        )
        self.journal = build_disposable_migration_intent_journal(
            self.db, operation_id="a" * 32,
            pinned_source_sha256=self.pins["pinned_source_sha256"],
            pinned_plan_sha256=self.pins["pinned_plan_sha256"],
            pinned_mapping_sha256=self.pins["pinned_mapping_sha256"])
        self.args = dict(db=self.db, journal=self.journal,
                         independent_journal_head_sha256=self.journal["head_sha256"],
                         fence_token="c" * 32, epoch=42, **self.pins)

    def tearDown(self):
        self.db.close()
        if self.old is None:
            os.environ.pop("BAM_EPHEMERAL_PG_TEST", None)
        else:
            os.environ["BAM_EPHEMERAL_PG_TEST"] = self.old

    def test_pinned_journal_and_semantics_are_checked_not_approved(self):
        before = self.db.total_changes
        first = rehearse_pinned_disposable_protocol(**self.args)
        again = rehearse_pinned_disposable_protocol(
            **{**self.args, "release_mode": "abandoned_connection"})
        self.assertEqual(self.db.total_changes, before)
        self.assertEqual(first["intent_stages"], 7)
        self.assertGreater(first["unreviewed_semantic_column_signals"], 100)
        self.assertTrue(first["metadata_source_mapping_plan_pins_match"])
        self.assertTrue(first["external_intent_head_matches_hash_chain"])
        self.assertTrue(first["preview_and_semantic_fingerprints_match"])
        self.assertEqual(first["synthetic_receipt_head_sha256"],
                         again["synthetic_receipt_head_sha256"])
        for value in (first, again):
            self.assertTrue(value["synthetic_payload_rolled_back"])
            self.assertFalse(value["semantic_transforms_approved"])
            self.assertFalse(value["source_fixture_writes_performed"])
            self.assertFalse(value["external_pin_custody_proven"])
            self.assertFalse(value["journal_signatures_authenticated"])
            self.assertFalse(value["independent_operator_authorization_proven"])
            self.assertFalse(value["persistent_replay_authority_implemented"])
            self.assertFalse(value["postgres_connected"])
            self.assertFalse(value["cutover_permitted"])

    def test_tamper_replay_partial_journal_and_pin_drift_block_rehearsal(self):
        short = build_disposable_migration_intent_journal(
            self.db, operation_id="a" * 32, through_sequence=4,
            pinned_source_sha256=self.pins["pinned_source_sha256"],
            pinned_plan_sha256=self.pins["pinned_plan_sha256"],
            pinned_mapping_sha256=self.pins["pinned_mapping_sha256"])
        modified = copy.deepcopy(self.journal)
        modified["events"][1]["intent"] = "executed"
        for changes in (
            {"independent_journal_head_sha256": "f" * 64},
            {"journal": modified},
            {"journal": short, "independent_journal_head_sha256": short["head_sha256"]},
            {"pinned_source_sha256": "f" * 64},
            {"pinned_plan_sha256": "f" * 64},
            {"pinned_mapping_sha256": "f" * 64},
            {"pinned_preview_sha256": "f" * 64},
            {"pinned_semantics_sha256": "f" * 64},
        ):
            with self.subTest(change=list(changes)):
                with patch("neon_disposable_protocol_binding.rehearse_disposable_versioned_protocol") as forbidden:
                    with self.assertRaises(PermissionError):
                        rehearse_pinned_disposable_protocol(
                            **{**self.args, **changes})
                    forbidden.assert_not_called()

    def test_private_values_are_not_returned_and_schema_drift_blocks(self):
        secret = "SOURCE_PRIVATE_REQUEST_9866"
        self.gateway.directory.bootstrap_owner("PRIVATE_TENANT_9866", "owner")
        self.gateway.requests.create(
            tenant_id="PRIVATE_TENANT_9866", channel="facebook",
            draft_text=secret, suggestion="photo",
            required_items=["image"], now=1234)
        count = self.db.total_changes
        result = rehearse_pinned_disposable_protocol(**self.args)
        self.assertEqual(self.db.total_changes, count)
        self.assertNotIn(secret, str(result))
        self.assertNotIn("PRIVATE_TENANT_9866", str(result))
        self.db.execute("ALTER TABLE content_requests ADD COLUMN unexpected TEXT")
        with patch("neon_disposable_protocol_binding.rehearse_disposable_versioned_protocol") as forbidden:
            with self.assertRaises(PermissionError):
                rehearse_pinned_disposable_protocol(**self.args)
            forbidden.assert_not_called()

    def test_non_ci_mode_rejected_before_metadata_and_protocol(self):
        os.environ.pop("BAM_EPHEMERAL_PG_TEST", None)
        with patch("neon_disposable_protocol_binding.inspect_disposable_migration_intent_journal") as forbidden:
            with self.assertRaises(PermissionError):
                rehearse_pinned_disposable_protocol(**self.args)
            forbidden.assert_not_called()
        os.environ["BAM_EPHEMERAL_PG_TEST"] = "1"
        with self.assertRaises(TypeError):
            rehearse_pinned_disposable_protocol(
                **{**self.args, "db": object()})


if __name__ == "__main__":
    unittest.main()
