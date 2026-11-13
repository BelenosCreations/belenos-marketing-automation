"""Negative CI-only tests of disposable authenticated on-disk replay receipts."""
import os
import sqlite3
import unittest
from unittest.mock import patch

from neon_disposable_durable_replay_ledger import (
    _DisposableDurableReplayLedger, _GENESIS,
    rehearse_disposable_durable_replay,
)


class DurableSyntheticReplayTests(unittest.TestCase):
    def setUp(self):
        self.old = os.environ.get("BAM_EPHEMERAL_PG_TEST")
        os.environ["BAM_EPHEMERAL_PG_TEST"] = "1"
        self.key = b"k" * 32
        self.args = dict(operation_id="a" * 32, intent_head="b" * 64,
                         fence_token="c" * 32, epoch=11)

    def tearDown(self):
        if self.old is None:
            os.environ.pop("BAM_EPHEMERAL_PG_TEST", None)
        else:
            os.environ["BAM_EPHEMERAL_PG_TEST"] = self.old

    def test_reconnect_and_replay_are_durable_inside_disposable_file(self):
        ledger = _DisposableDurableReplayLedger(signing_key=self.key)
        location = ledger._path
        try:
            head = ledger.reserve(
                **self.args, independently_pinned_head=_GENESIS)
            ledger.reopen()
            self.assertEqual(ledger.inspect(
                independently_pinned_head=head)["synthetic_receipts"], 1)
            with self.assertRaises(PermissionError):
                ledger.reserve(**self.args, independently_pinned_head=head)
            with self.assertRaises(PermissionError):
                ledger.advance(**self.args, stage=2,
                               independently_pinned_head=head)
            for step in range(1, 8):
                old_head = head
                head = ledger.advance(**self.args, stage=step,
                                      independently_pinned_head=head)
                self.assertNotEqual(old_head, head)
                if step == 4:
                    ledger.reopen()
                    with self.assertRaises(PermissionError):
                        ledger.advance(**self.args, stage=5,
                                       independently_pinned_head=old_head)
            ledger.reopen()
            self.assertEqual(ledger.inspect(
                independently_pinned_head=head)["synthetic_receipts"], 8)
            for stage in (0, 8, True, "7", -1):
                with self.assertRaises(PermissionError):
                    ledger.advance(**self.args, stage=stage,
                                   independently_pinned_head=head)
            head = ledger.abort(**self.args, independently_pinned_head=head)
            ledger.reopen()
            self.assertEqual(ledger.inspect(
                independently_pinned_head=head)["synthetic_receipts"], 9)
            with self.assertRaises(PermissionError):
                ledger.abort(**self.args, independently_pinned_head=head)
            with self.assertRaises(PermissionError):
                ledger.advance(**self.args, stage=7,
                               independently_pinned_head=head)
            with self.assertRaises(PermissionError):
                ledger.reserve(**self.args, independently_pinned_head=head)
            # A distinct operation may use a *higher* epoch only after abort.
            next_args = {**self.args, "operation_id": "d" * 32, "epoch": 12}
            with self.assertRaises(PermissionError):
                ledger.reserve(**{**next_args, "epoch": 11},
                               independently_pinned_head=head)
            new_head = ledger.reserve(**next_args, independently_pinned_head=head)
            self.assertEqual(ledger.inspect(
                independently_pinned_head=new_head)["synthetic_operations"], 2)
        finally:
            ledger.close()
        self.assertFalse(os.path.exists(location))

    def test_context_stale_heads_tokens_epochs_and_active_race(self):
        ledger = _DisposableDurableReplayLedger(signing_key=self.key)
        try:
            head = ledger.reserve(**self.args, independently_pinned_head=_GENESIS)
            for changes in (
                {"independently_pinned_head": _GENESIS},
                {"intent_head": "f" * 64},
                {"fence_token": "e" * 32},
                {"epoch": 12},
                {"epoch": True},
            ):
                with self.subTest(changes=changes):
                    with self.assertRaises((PermissionError, ValueError)):
                        ledger.advance(**{**self.args, "stage": 1,
                                           "independently_pinned_head": head,
                                           **changes})
            with self.assertRaises(PermissionError):
                ledger.reserve(operation_id="e" * 32,
                               intent_head="b" * 64,
                               fence_token="c" * 32, epoch=12,
                               independently_pinned_head=head)
            self.assertEqual(ledger.inspect(
                independently_pinned_head=head)["synthetic_receipts"], 1)
            competitor = sqlite3.connect(ledger._path, timeout=0,
                                         isolation_level=None)
            try:
                ledger._db.execute("BEGIN IMMEDIATE")
                with self.assertRaises(sqlite3.OperationalError):
                    competitor.execute("BEGIN IMMEDIATE")
                ledger._db.execute("ROLLBACK")
            finally:
                competitor.close()
        finally:
            ledger.close()

    def test_hmac_chain_catches_tamper_and_unsigned_state_mutations(self):
        for statement in (
            "UPDATE ci_events SET stage=7 WHERE sequence=1",
            "DELETE FROM ci_events WHERE sequence=1",
            "UPDATE ci_operations SET status='aborted'",
            "UPDATE ci_meta SET head='" + "f" * 64 + "'",
        ):
            ledger = _DisposableDurableReplayLedger(signing_key=self.key)
            try:
                head = ledger.reserve(**self.args,
                                      independently_pinned_head=_GENESIS)
                ledger._db.execute(statement)
                with self.assertRaises(PermissionError):
                    ledger.inspect(independently_pinned_head=head)
                with self.assertRaises(PermissionError):
                    ledger.advance(**self.args, stage=1,
                                   independently_pinned_head=head)
            finally:
                ledger.close()
        ledger = _DisposableDurableReplayLedger(signing_key=self.key)
        try:
            head = ledger.reserve(**self.args,
                                  independently_pinned_head=_GENESIS)
            ledger._key = b"x" * 32
            with self.assertRaises(PermissionError):
                ledger.inspect(independently_pinned_head=head)
        finally:
            ledger.close()

    def test_mode_and_unsafe_file_permissions_block_use(self):
        for changes in (
            {"operation_id": "bad"}, {"intent_head": "x" * 64},
            {"fence_token": "not-token"}, {"epoch": True},
            {"epoch": 0}, {"epoch": 2 ** 60},
        ):
            ledger = _DisposableDurableReplayLedger(signing_key=self.key)
            try:
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    ledger.reserve(**{**self.args, **changes},
                                   independently_pinned_head=_GENESIS)
            finally:
                ledger.close()
        ledger = _DisposableDurableReplayLedger(signing_key=self.key)
        try:
            os.chmod(ledger._path, 0o644)
            with self.assertRaises(PermissionError):
                ledger.reopen()
        finally:
            ledger.close()
        self.assertFalse(
            rehearse_disposable_durable_replay(
                signing_key=self.key, **self.args)["production_ready"])
        os.environ.pop("BAM_EPHEMERAL_PG_TEST")
        with patch("neon_disposable_durable_replay_ledger.sqlite3.connect") as forbidden:
            with self.assertRaises(PermissionError):
                rehearse_disposable_durable_replay(
                    signing_key=self.key, **self.args)
            forbidden.assert_not_called()


if __name__ == "__main__":
    unittest.main()
