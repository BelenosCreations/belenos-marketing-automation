"""Offline operator-preflight safety and drift regressions."""
import sqlite3
import unittest

from bam_offline_gateway import BAMOfflineGateway
from neon_migration_operator_preflight import (
    inactive_pg_schema_manifest, inspect_inactive_migration_preflight)


class OperatorMigrationPreflightTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.app = BAMOfflineGateway(self.db, enabled=False)

    def tearDown(self):
        self.db.close()

    def test_stable_manifest_and_no_sql_or_secret_exposure(self):
        one = inactive_pg_schema_manifest()
        self.assertEqual(one, inactive_pg_schema_manifest())
        self.assertEqual(one["reviewed_table_count"], 46)
        self.assertEqual(len(one["phases"]), 8)
        self.assertEqual([p["version"] for p in one["phases"]],
                         list(range(1, 9)))
        self.assertFalse(one["production_approved"])
        self.assertNotIn("CREATE TABLE", str(one))

    def test_fresh_fixture_remains_explicitly_cutover_blocked(self):
        report = inspect_inactive_migration_preflight(self.db)
        self.assertFalse(report["cutover_permitted"])
        self.assertFalse(report["rollback_executable"])
        self.assertFalse(report["postgres_connection_attempted"])
        self.assertFalse(report["customer_records_exported"])
        self.assertIn("source_schema_fingerprint_not_pinned", report["blockers"])
        self.assertIn("independent_restoration_and_cross_tenant_parity_acceptance",
                      report["blockers"])
        self.assertEqual(report["preview_table_count"], 46)
        self.assertFalse(report["publishing_enabled"])

    def test_operator_pin_is_not_a_migration_authorization(self):
        first = inspect_inactive_migration_preflight(self.db)
        pinned = inspect_inactive_migration_preflight(
            self.db, pinned_source_digest=first["source_schema_sha256"])
        self.assertTrue(pinned["pinned_schema_matches"])
        self.assertFalse(pinned["cutover_permitted"])
        self.assertNotIn("source_schema_fingerprint_not_pinned",
                         pinned["blockers"])
        self.db.execute("CREATE TABLE new_unreviewed_table(id INTEGER PRIMARY KEY)")
        drifted = inspect_inactive_migration_preflight(
            self.db, pinned_source_digest=first["source_schema_sha256"])
        self.assertIn("pinned_source_schema_drift", drifted["blockers"])
        self.assertIn("new_unreviewed_table", drifted["unreviewed_source_table_names"])
        self.assertIn("unreviewed_source_tables", drifted["blockers"])

    def test_invalid_inputs_rejected_without_network_or_ddl(self):
        with self.assertRaises(TypeError):
            inspect_inactive_migration_preflight(object())
        for value in (True, "not-a-digest", "G" * 64, 123):
            with self.subTest(value=value), self.assertRaises(ValueError):
                inspect_inactive_migration_preflight(
                    self.db, pinned_source_digest=value)

    def test_account_values_are_never_returned(self):
        self.app.directory.bootstrap_owner("PRIVATE_BAM_CLIENT_89", "owner")
        from access_policy import Principal, Role
        token = self.app.sessions.issue(
            Principal("owner", "PRIVATE_BAM_CLIENT_89", Role.OWNER), now=10)
        self.app.requests.create(
            tenant_id="PRIVATE_BAM_CLIENT_89", channel="facebook",
            draft_text="SECRET_DRAFT_TEXT_293f", suggestion="photo",
            required_items=["image"], now=10)
        result = inspect_inactive_migration_preflight(self.db)
        self.assertNotIn(token, str(result))
        self.assertNotIn("PRIVATE_BAM_CLIENT_89", str(result))
        self.assertNotIn("SECRET_DRAFT_TEXT_293f", str(result))
        self.assertNotIn("CREATE TABLE", str(result))


if __name__ == "__main__":
    unittest.main()
