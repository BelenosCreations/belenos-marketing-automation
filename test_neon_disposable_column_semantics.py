"""Adversarial, in-memory-only semantic migration review regressions."""
import os
import sqlite3
import unittest

from bam_offline_gateway import BAMOfflineGateway
from neon_disposable_column_semantics import (
    _split_table_declarations, compile_disposable_semantic_review,
)


class DisposableColumnSemanticTests(unittest.TestCase):
    def setUp(self):
        self.old = os.environ.get("BAM_EPHEMERAL_PG_TEST")
        os.environ["BAM_EPHEMERAL_PG_TEST"] = "1"
        self.db = sqlite3.connect(":memory:")
        self.gateway = BAMOfflineGateway(self.db, enabled=False)

    def tearDown(self):
        self.db.close()
        if self.old is None:
            os.environ.pop("BAM_EPHEMERAL_PG_TEST", None)
        else:
            os.environ["BAM_EPHEMERAL_PG_TEST"] = self.old

    def _review(self, **overrides):
        return compile_disposable_semantic_review(self.db, **overrides)

    def test_unapproved_deterministic_semantic_inventory(self):
        first = self._review()
        self.assertEqual(first, self._review())
        self.assertEqual(first["table_count"], 46)
        self.assertGreater(first["column_count"], 100)
        self.assertEqual(len(first["semantics_sha256"]), 64)
        self.assertFalse(first["cutover_permitted"])
        self.assertFalse(first["raw_default_expressions_returned"])
        self.assertFalse(first["postgres_connected"])
        by_table = {row["table"]: row for row in first["tables"]}
        content = {row["column"]: row for row in by_table["content_requests"]["columns"]}
        self.assertTrue(content["required_items"]["json_text_semantics_review_required"])
        self.assertTrue(content["tenant_id"]["tenant_or_reference_review_required"])
        self.assertTrue(content["provided_items"]["target_has_default"])
        self.assertFalse(content["provided_items"]["value_and_constraint_reviewed"])
        self.assertTrue(any(row["generated_identity_reseed_review_required"]
                            for row in first["tables"]))
        self.assertNotIn("CREATE TABLE", str(first))

    def test_independent_pins_do_not_allow_promotion(self):
        baseline = self._review()
        checked = self._review(
            pinned_source_sha256=baseline["source_schema_sha256"],
            pinned_mapping_sha256=baseline["mapping_sha256"],
            pinned_preview_sha256=baseline["preview_sha256"],
            pinned_semantics_sha256=baseline["semantics_sha256"])
        self.assertTrue(all(checked["independent_pin_matches"].values()))
        self.assertFalse(checked["all_semantics_approved"])
        self.assertFalse(checked["rollback_executable"])
        changed = self._review(pinned_semantics_sha256="0" * 64)
        self.assertFalse(changed["independent_pin_matches"]["semantics"])
        self.assertIn("independent_semantics_pin_missing_or_drift",
                      changed["blockers"])
        self.db.execute("ALTER TABLE content_requests ADD COLUMN surprise TEXT")
        drift = self._review(
            pinned_source_sha256=baseline["source_schema_sha256"],
            pinned_mapping_sha256=baseline["mapping_sha256"],
            pinned_preview_sha256=baseline["preview_sha256"],
            pinned_semantics_sha256=baseline["semantics_sha256"])
        self.assertFalse(drift["independent_pin_matches"]["source"])
        self.assertFalse(drift["independent_pin_matches"]["semantics"])
        self.assertIn("source_target_column_shape_mismatch", drift["blockers"])

    def test_no_rows_or_default_literals_disclosed(self):
        secret = "SECRET_SHOULD_NOT_LEAVE_DB_307"
        self.gateway.directory.bootstrap_owner("TENANT_PRIVATE_307", "owner")
        self.gateway.requests.create(tenant_id="TENANT_PRIVATE_307",
            channel="facebook", draft_text=secret, suggestion="photo",
            required_items=["image"], now=10)
        before = self.db.total_changes
        report = self._review()
        self.assertEqual(self.db.total_changes, before)
        self.assertNotIn(secret, str(report))
        self.assertNotIn("TENANT_PRIVATE_307", str(report))
        self.assertFalse(report["customer_rows_read"])

    def test_quote_aware_pg_ddl_split_and_fail_closed(self):
        clauses = _split_table_declarations(
            "CREATE TABLE example (a TEXT DEFAULT 'x,y', "
            "b INTEGER CHECK (b IN (1,2)), PRIMARY KEY(a,b))")
        self.assertEqual(len(clauses), 3)
        self.assertIn("'x,y'", clauses[0])
        self.assertIn("(1,2)", clauses[1])
        with self.assertRaises(ValueError):
            _split_table_declarations("CREATE TABLE bad (a TEXT, ")
        with self.assertRaises(ValueError):
            _split_table_declarations("SELECT * FROM secret")

    def test_disabled_mode_and_invalid_external_pins(self):
        with self.assertRaises(TypeError):
            compile_disposable_semantic_review(object())
        for value in (True, 0, "ABC", "Z" * 64):
            with self.subTest(pin=value), self.assertRaises(ValueError):
                self._review(pinned_semantics_sha256=value)
        os.environ.pop("BAM_EPHEMERAL_PG_TEST", None)
        with self.assertRaises(PermissionError):
            self._review()


if __name__ == "__main__":
    unittest.main()
