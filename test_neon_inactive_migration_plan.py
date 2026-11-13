"""Negative acceptance tests for inactive migration-plan metadata."""
import sqlite3
import unittest

from bam_offline_gateway import BAMOfflineGateway
from neon_inactive_migration_plan import compile_inactive_migration_plan


class InactivePlanTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.gateway = BAMOfflineGateway(self.db, enabled=False)

    def tearDown(self):
        self.db.close()

    def test_deterministic_blocked_source_to_target_plan(self):
        p = compile_inactive_migration_plan(self.db)
        self.assertEqual(p, compile_inactive_migration_plan(self.db))
        self.assertEqual(len(p["schema_phases"]), 8)
        self.assertEqual(len(p["operator_steps"]), 8)
        self.assertEqual(len(p["plan_sha256"]), 64)
        self.assertFalse(p["cutover_permitted"])
        self.assertFalse(p["rows_copied"])
        self.assertFalse(p["postgres_connected"])
        self.assertFalse(p["transactional_execution_implemented"])
        self.assertFalse(p["rollback_executable"])
        self.assertTrue(all(not x["executable"] for x in p["operator_steps"]))
        self.assertTrue(all(not row["row_transform_reviewed"]
                            for row in p["source_table_mapping"]))
        self.assertNotIn("CREATE TABLE", str(p))
        self.assertNotIn("INSERT INTO", str(p))

    def test_independent_schema_and_plan_pins_do_not_authorize_execution(self):
        initial = compile_inactive_migration_plan(self.db)
        pinned = compile_inactive_migration_plan(
            self.db, pinned_source_sha256=initial["source_schema_sha256"],
            pinned_plan_sha256=initial["plan_sha256"])
        self.assertTrue(pinned["source_schema_pin_matches"])
        self.assertTrue(pinned["plan_pin_matches"])
        self.assertFalse(pinned["cutover_permitted"])
        self.assertIn("customer_data_export_and_postgresql_runner_disabled",
                      pinned["blockers"])
        self.db.execute("CREATE TABLE new_extra_table(id INTEGER PRIMARY KEY)")
        drift = compile_inactive_migration_plan(
            self.db, pinned_source_sha256=initial["source_schema_sha256"],
            pinned_plan_sha256=initial["plan_sha256"])
        self.assertFalse(drift["plan_pin_matches"])
        self.assertIn("pinned_source_schema_drift", drift["blockers"])
        self.assertIn("independently_pinned_execution_plan_drift", drift["blockers"])
        self.assertIn("new_extra_table", drift["unreviewed_source_tables"])

    def test_data_is_not_exposed_or_modified(self):
        self.gateway.directory.bootstrap_owner("PRIVATE_TENANT_XYZ", "owner")
        self.gateway.requests.create(
            tenant_id="PRIVATE_TENANT_XYZ", channel="facebook",
            draft_text="SENSITIVE_DRAFT_991", suggestion="photo",
            required_items=["image"], now=10)
        before = self.db.total_changes
        result = compile_inactive_migration_plan(self.db)
        self.assertEqual(self.db.total_changes, before)
        self.assertNotIn("SENSITIVE_DRAFT_991", str(result))
        self.assertNotIn("PRIVATE_TENANT_XYZ", str(result))
        self.assertFalse(result["source_writes_performed"])

    def test_rejects_untrusted_and_malformed_pins(self):
        with self.assertRaises(TypeError):
            compile_inactive_migration_plan(object())
        for pin in (True, -1, "A" * 64, "abc", "x" * 64):
            with self.subTest(pin=pin), self.assertRaises(ValueError):
                compile_inactive_migration_plan(
                    self.db, pinned_plan_sha256=pin)
        for pin in (None, "0" * 64):
            p = compile_inactive_migration_plan(
                self.db, pinned_source_sha256=pin)
            self.assertFalse(p["cutover_permitted"])


if __name__ == "__main__":
    unittest.main()
