"""Independent writer and rollback canaries never simulate production approval."""
import os
import unittest
from unittest.mock import patch

from neon_disposable_writer_fence import rehearse_disposable_writer_fence


class DisposableWriterFenceTests(unittest.TestCase):
    def setUp(self):
        self.previous = os.environ.get("BAM_EPHEMERAL_PG_TEST")
        os.environ["BAM_EPHEMERAL_PG_TEST"] = "1"

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("BAM_EPHEMERAL_PG_TEST", None)
        else:
            os.environ["BAM_EPHEMERAL_PG_TEST"] = self.previous

    def test_rollback_releases_writer_lock_and_never_migrates_data(self):
        report = rehearse_disposable_writer_fence()
        self.assertEqual(report, rehearse_disposable_writer_fence())
        self.assertTrue(report["synthetic_competing_writer_blocked"])
        self.assertTrue(report["uncommitted_synthetic_row_rolled_back"])
        self.assertTrue(report["post_release_synthetic_writer_succeeded"])
        self.assertEqual(len(report["synthetic_evidence_sha256"]), 64)
        self.assertFalse(report["real_application_write_fence_implemented"])
        self.assertFalse(report["customer_database_opened"])
        self.assertFalse(report["postgres_transaction_started"])
        self.assertFalse(report["production_rollback_executable"])
        self.assertFalse(report["cutover_permitted"])

    def test_abandoned_connection_releases_lock_without_leaking_uncommitted(self):
        report = rehearse_disposable_writer_fence(
            release_mode="abandoned_connection")
        self.assertEqual(report["release_mode"], "abandoned_connection")
        self.assertTrue(report["uncommitted_synthetic_row_rolled_back"])
        self.assertFalse(report["production_ready"])
        self.assertNotEqual(report["synthetic_evidence_sha256"],
                            rehearse_disposable_writer_fence()[
                                "synthetic_evidence_sha256"])

    def test_modes_fail_closed_and_disabled_gate_stops_connect(self):
        for mode in ("commit", "publish", None, 1, True):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                rehearse_disposable_writer_fence(release_mode=mode)
        os.environ.pop("BAM_EPHEMERAL_PG_TEST")
        with patch("neon_disposable_writer_fence.sqlite3.connect") as forbidden:
            with self.assertRaises(PermissionError):
                rehearse_disposable_writer_fence()
            forbidden.assert_not_called()


if __name__ == "__main__":
    unittest.main()
