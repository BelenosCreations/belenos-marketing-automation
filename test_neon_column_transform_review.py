"""Conservative negative checks for offline migration column/type review."""
import sqlite3
import unittest

from bam_offline_gateway import BAMOfflineGateway
from neon_column_transform_review import compile_offline_column_transform_review


class ColumnTransformReviewTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.app = BAMOfflineGateway(self.db, enabled=False)

    def tearDown(self):
        self.db.close()

    def test_all_target_columns_proposed_but_never_authorized(self):
        review = compile_offline_column_transform_review(self.db)
        self.assertEqual(review, compile_offline_column_transform_review(self.db))
        self.assertEqual(review["mapped_target_table_count"], 46)
        self.assertGreater(review["mapped_target_column_count"], 100)
        self.assertEqual(len(review["mapping_sha256"]), 64)
        self.assertFalse(review["customer_rows_read"])
        self.assertFalse(review["postgres_connected"])
        self.assertFalse(review["cutover_permitted"])
        self.assertFalse(review["all_columns_independently_approved"])
        for table in review["mappings"]:
            self.assertFalse(table["independently_reviewed"])
            for column in table["columns"]:
                self.assertFalse(column["value_transform_reviewed"])
                self.assertFalse(column["tenant_semantics_reviewed"])
        self.assertNotIn("CREATE TABLE", str(review))

    def test_integer_and_binary_review_are_explicit(self):
        review = compile_offline_column_transform_review(self.db)
        by_table = {t["target_table"]: t for t in review["mappings"]}
        password = {c["column"]: c for c in
                    by_table["bam_password_credentials"]["columns"]}
        self.assertEqual(password["salt"]["target_type"], "BYTEA")
        self.assertEqual(password["salt"]["candidate_conversion"],
                         "blob_to_bytea_binary_adapter_review")
        identity = {c["column"]: c for c in
                    by_table["bam_identities"]["columns"]}
        self.assertEqual(identity["created_at"]["target_type"], "BIGINT")
        self.assertIn("integer_range", identity["created_at"]["candidate_conversion"])
        self.assertTrue(any(t["identity_sequence_requires_reseed_review"]
                            for t in review["mappings"]))

    def test_independent_pins_never_approve_and_schema_change_fails(self):
        baseline = compile_offline_column_transform_review(self.db)
        checked = compile_offline_column_transform_review(
            self.db, pinned_source_sha256=baseline["source_schema_sha256"],
            pinned_mapping_sha256=baseline["mapping_sha256"])
        self.assertTrue(checked["source_pin_matches"])
        self.assertTrue(checked["mapping_pin_matches"])
        self.assertFalse(checked["cutover_permitted"])
        self.db.execute("ALTER TABLE content_requests ADD COLUMN mystery TEXT")
        drift = compile_offline_column_transform_review(
            self.db, pinned_source_sha256=baseline["source_schema_sha256"],
            pinned_mapping_sha256=baseline["mapping_sha256"])
        self.assertFalse(drift["source_pin_matches"])
        self.assertFalse(drift["mapping_pin_matches"])
        self.assertIn("content_requests", drift["column_shape_mismatch_tables"])
        self.assertIn("independent_mapping_pin_drift", drift["blockers"])

    def test_customer_values_never_leave_metadata(self):
        self.app.directory.bootstrap_owner("HIDDEN_TENANT_23", "owner")
        self.app.requests.create(
            tenant_id="HIDDEN_TENANT_23", channel="facebook",
            draft_text="HIDDEN_DRAFT_928", suggestion="photo",
            required_items=["image"], now=10)
        before = self.db.total_changes
        result = compile_offline_column_transform_review(self.db)
        self.assertEqual(before, self.db.total_changes)
        self.assertNotIn("HIDDEN_TENANT_23", str(result))
        self.assertNotIn("HIDDEN_DRAFT_928", str(result))
        self.assertFalse(result["source_writes_performed"])

    def test_bad_pins_and_untrusted_connection_rejected(self):
        with self.assertRaises(TypeError):
            compile_offline_column_transform_review(object())
        for pin in (True, 0, "INVALID", "Z" * 64):
            with self.subTest(pin=pin), self.assertRaises(ValueError):
                compile_offline_column_transform_review(
                    self.db, pinned_mapping_sha256=pin)


if __name__ == "__main__":
    unittest.main()
