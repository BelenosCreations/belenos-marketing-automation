"""Synthetic-only strict type adapter and independent pin regressions."""
import os
import sqlite3
import unittest

from audience_observation_store import AudienceObservationStore
from bam_offline_gateway import BAMOfflineGateway
from neon_column_transform_review import compile_offline_column_transform_review
from neon_synthetic_type_acceptance import inspect_disposable_typed_cell


class SyntheticTypeAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.prior = os.environ.get("BAM_EPHEMERAL_PG_TEST")
        os.environ["BAM_EPHEMERAL_PG_TEST"] = "1"
        self.db = sqlite3.connect(":memory:")
        self.gateway = BAMOfflineGateway(self.db, enabled=False)
        # This optional table is lazily initialized by the feature store.
        self.audience = AudienceObservationStore(self.db)
        report = compile_offline_column_transform_review(self.db)
        self.source = report["source_schema_sha256"]
        self.mapping = report["mapping_sha256"]

    def tearDown(self):
        self.db.close()
        if self.prior is None:
            os.environ.pop("BAM_EPHEMERAL_PG_TEST", None)
        else:
            os.environ["BAM_EPHEMERAL_PG_TEST"] = self.prior

    def inspect(self, table, column, value, **kw):
        args = dict(db=self.db, table=table, column=column, value=value,
                    pinned_source_sha256=self.source,
                    pinned_mapping_sha256=self.mapping)
        args.update(kw)
        return inspect_disposable_typed_cell(**args)

    def test_text_binary_integer_and_double_candidates_are_not_approvals(self):
        cases = [
            ("bam_identities", "subject_id", "synthetic-tenant-1", "TEXT"),
            ("bam_identities", "created_at", 2**63 - 1, "BIGINT"),
            ("bam_password_credentials", "salt", b"\x00\xffABC", "BYTEA"),
            ("bam_password_credentials", "iterations", 2**31 - 1, "INTEGER"),
            ("audience_observations", "engagement_rate", 0.25,
             "DOUBLE PRECISION"),
        ]
        for table, column, value, expected in cases:
            with self.subTest(column=column):
                before = self.db.total_changes
                result = self.inspect(table, column, value)
                self.assertEqual(result["target_type"], expected)
                self.assertEqual(len(result["synthetic_cell_sha256"]), 64)
                self.assertFalse(result["migration_executable"])
                self.assertFalse(result["row_transform_approved"])
                self.assertFalse(result["customer_records_read"])
                self.assertFalse(result["postgres_connected"])
                self.assertFalse(result["raw_value_returned"])
                self.assertEqual(before, self.db.total_changes)

    def test_no_silent_integer_coercion_overflow_or_boolean(self):
        for value in (True, 2**63, -(2**63) - 1, 1.0, "1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.inspect("bam_identities", "created_at", value)
        for value in (2**31, -(2**31)-1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.inspect("bam_password_credentials", "iterations", value)

    def test_float_nonfinite_and_text_integrity(self):
        for value in (float("nan"), float("inf"), float("-inf"), 1, "0.2"):
            with self.subTest(value=str(value)), self.assertRaises(ValueError):
                self.inspect("audience_observations", "engagement_rate", value)
        for value in ("a\x00b", "\ud800", "x" * 4097, b"bytes"):
            with self.subTest(value=str(value)[:12]), self.assertRaises(ValueError):
                self.inspect("bam_identities", "subject_id", value)
        with self.assertRaises(ValueError):
            self.inspect("bam_password_credentials", "salt", bytearray(b"x"))
        with self.assertRaises(ValueError):
            self.inspect("bam_password_credentials", "salt", b"x" * 4097)

    def test_null_and_unpinned_or_changed_schema_fail_closed(self):
        with self.assertRaises(ValueError):
            self.inspect("bam_identities", "email", None)
        with self.assertRaises(PermissionError):
            self.inspect("bam_identities", "email", "test@example.org",
                         pinned_mapping_sha256="0"*64)
        with self.assertRaises(PermissionError):
            self.inspect("bam_identities", "email", "test@example.org",
                         pinned_source_sha256="f"*64)
        self.db.execute("ALTER TABLE bam_identities ADD COLUMN surprise TEXT")
        with self.assertRaises(PermissionError):
            self.inspect("bam_identities", "email", "test@example.org")

    def test_unknown_name_private_output_and_disabled_mode(self):
        with self.assertRaises(ValueError):
            self.inspect("missing_table", "col", "value")
        with self.assertRaises(ValueError):
            self.inspect("bam_identities", "missing_col", "value")
        secret = "SYNTHETIC_PRIVATE_SAMPLE_492"
        result = self.inspect("bam_identities", "email", secret)
        self.assertNotIn(secret, str(result))
        self.assertEqual(result["table"], "bam_identities")
        os.environ.pop("BAM_EPHEMERAL_PG_TEST")
        with self.assertRaises(PermissionError):
            self.inspect("bam_identities", "email", secret)


if __name__ == "__main__":
    unittest.main()
