"""Adversarial CI-only v1 transaction protocol / rollback tests."""
import os
import unittest
from unittest.mock import patch

from neon_disposable_versioned_protocol import (
    _DisposableProtocol, rehearse_disposable_versioned_protocol,
)


class DisposableVersionedProtocolTests(unittest.TestCase):
    def setUp(self):
        self.previous = os.environ.get("BAM_EPHEMERAL_PG_TEST")
        os.environ["BAM_EPHEMERAL_PG_TEST"] = "1"
        self.kwargs = dict(operation_id="a" * 32, journal_head="b" * 64,
                           fence_token="c" * 32, epoch=23)

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("BAM_EPHEMERAL_PG_TEST", None)
        else:
            os.environ["BAM_EPHEMERAL_PG_TEST"] = self.previous

    def test_two_disposable_rollback_scenarios_are_deterministic_and_blocked(self):
        a = rehearse_disposable_versioned_protocol(**self.kwargs)
        b = rehearse_disposable_versioned_protocol(
            **self.kwargs, release_mode="abandoned_connection")
        self.assertEqual(a, rehearse_disposable_versioned_protocol(**self.kwargs))
        self.assertEqual(a["synthetic_stages_exercised"], 7)
        self.assertEqual(a["synthetic_receipt_head_sha256"],
                         b["synthetic_receipt_head_sha256"])
        for report in (a, b):
            self.assertTrue(report["synthetic_competing_writer_blocked"])
            self.assertTrue(report["synthetic_payload_rolled_back"])
            self.assertTrue(report["operation_terminally_aborted"])
            for name in (
                "external_head_authenticity_verified",
                "persistent_replay_authority_implemented",
                "independent_operator_approval_proven",
                "application_writers_fenced", "background_workers_fenced",
                "postgres_connected", "postgres_transaction_started",
                "customer_database_opened", "customer_rows_read",
                "production_restore_rehearsed", "promotion_authorized",
                "cutover_permitted", "publishing_enabled", "production_ready",
            ):
                self.assertFalse(report[name], name)

    def test_atomic_stage_receipts_and_step_replay_refused(self):
        p = _DisposableProtocol(**self.kwargs)
        try:
            p.reserve()
            with self.assertRaises(PermissionError):
                p.reserve(connection=p.contender)
            with self.assertRaises(PermissionError):
                p.advance(2)
            first = p.advance(1)
            self.assertEqual(p.inspect_chain()["head_sha256"], first)
            for number, options in (
                (1, {}), (3, {}), (2, {"epoch": 24}),
                (2, {"epoch": True}), (2, {"fence_token": "d" * 32}),
                (2, {"journal_head": "f" * 64}),
                (8, {}), (0, {}), (True, {}), ("2", {}),
            ):
                with self.subTest(step=number, options=options):
                    with self.assertRaises(PermissionError):
                        p.advance(number, **options)
            self.assertEqual(p.inspect_chain()["event_count"], 1)
            for n in range(2, 8):
                p.advance(n)
            self.assertEqual(p.inspect_chain()["event_count"], 7)
            with self.assertRaises(PermissionError):
                p.advance(8)
            p.abandon()
            with self.assertRaises(PermissionError):
                p.advance(7)
            with self.assertRaises(PermissionError):
                p.abandon(connection=p.contender)
            with self.assertRaises(PermissionError):
                p.reserve()
        finally:
            p.close()

    def test_tamper_detection_and_transaction_rollback(self):
        p = _DisposableProtocol(**self.kwargs)
        try:
            p.reserve()
            p.advance(1)
            p.contender.execute("""UPDATE ci_protocol_events
                SET event_head=? WHERE sequence=1""", ("0" * 64,))
            with self.assertRaises(PermissionError):
                p.inspect_chain()
            # Failed steps cannot add a receipt or increment an epoch.
            with self.assertRaises(PermissionError):
                p.advance(3)
            self.assertEqual(p.contender.execute(
                "SELECT count(*) FROM ci_protocol_events").fetchone()[0], 1)
        finally:
            p.close()

    def test_unrecognized_inputs_fail_closed_before_connect(self):
        cases = (
            {"operation_id": "A" * 32}, {"operation_id": "../customer"},
            {"journal_head": "0" * 63}, {"fence_token": 1},
            {"epoch": 0}, {"epoch": True}, {"epoch": 2 ** 40},
            {"version": 2}, {"version": True}, {"release_mode": "commit"},
        )
        for change in cases:
            values = {**self.kwargs, **change}
            with self.subTest(change=change):
                with self.assertRaises((ValueError, PermissionError)):
                    rehearse_disposable_versioned_protocol(**values)
        os.environ.pop("BAM_EPHEMERAL_PG_TEST", None)
        with patch("neon_disposable_versioned_protocol.sqlite3.connect") as forbidden:
            with self.assertRaises(PermissionError):
                rehearse_disposable_versioned_protocol(**self.kwargs)
            forbidden.assert_not_called()


if __name__ == "__main__":
    unittest.main()
