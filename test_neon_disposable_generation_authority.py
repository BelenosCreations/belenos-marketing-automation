"""Offline generation fence semantics: stale writers, crashes and replay."""
import os
import sqlite3
import unittest
from unittest.mock import patch
from neon_disposable_generation_authority import _DisposableGenerationAuthority

A = "a" * 32
B = "b" * 32
C = "c" * 32
T = "ci_tenant_a"


class TestGenerationAuthority(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"BAM_EPHEMERAL_PG_TEST": "1"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.authority = _DisposableGenerationAuthority()
        self.addCleanup(self.authority.close)

    def write(self, epoch, operation=A):
        return self.authority.write_canary(
            expected_epoch=epoch, operation_id=operation,
            tenant=T, marker="canary_alpha")

    def test_freeze_and_resume_reject_all_stale_generations(self):
        first = self.write(1)
        self.assertFalse(first["production_write"])
        frozen = self.authority.freeze(expected_epoch=1)
        self.assertEqual(frozen, 2)
        with self.assertRaises(PermissionError):
            self.write(1, B)
        with self.assertRaises(PermissionError):
            self.write(2, B)
        self.assertEqual(self.authority.state()["synthetic_committed_writes"], 1)
        self.authority.reopen()  # frozen mode survives another connection
        self.assertEqual(self.authority.state()["mode"], "frozen")
        reopened = self.authority.resume(expected_epoch=2)
        self.assertEqual(reopened, 3)
        with self.assertRaises(PermissionError):
            self.write(1, B)
        with self.assertRaises(PermissionError):
            self.write(2, B)
        self.assertTrue(self.write(3, B)["accepted"])
        self.assertEqual(self.authority.state()["synthetic_committed_writes"], 2)
        self.assertFalse(self.authority.state()["application_writers_fenced"])

    def test_replay_and_invalid_transitions_do_not_write(self):
        self.write(1)
        self.authority.reopen()
        with self.assertRaises(PermissionError):
            self.write(1)  # same ID after connection reopen
        with self.assertRaises(PermissionError):
            self.authority.resume(expected_epoch=1)
        self.assertEqual(self.authority.freeze(expected_epoch=1), 2)
        with self.assertRaises(PermissionError):
            self.authority.freeze(expected_epoch=1)
        with self.assertRaises(PermissionError):
            self.authority.resume(expected_epoch=1)
        self.assertEqual(self.authority.state()["synthetic_committed_writes"], 1)
        self.assertEqual(self.authority.state()["mode"], "frozen")

    def test_abandoned_uncommitted_write_rolls_back_on_close(self):
        db = self.authority._db  # controlled offline test-only interference
        db.execute("BEGIN IMMEDIATE")
        db.execute("INSERT INTO ci_writes VALUES(?,?,?,?)",
                   (A, T, 1, "canary_uncommitted"))
        self.authority.reopen()
        self.assertEqual(self.authority.state()["synthetic_committed_writes"], 0)
        self.assertEqual(self.authority.freeze(expected_epoch=1), 2)
        self.assertEqual(self.authority.state()["mode"], "frozen")

    def test_competing_transition_cannot_commit_while_writer_lock_held(self):
        other = self.authority._connect()
        try:
            self.authority._db.execute("BEGIN IMMEDIATE")
            with self.assertRaises(sqlite3.OperationalError):
                other.execute("BEGIN IMMEDIATE")
            self.authority._db.execute("ROLLBACK")
            other.execute("BEGIN IMMEDIATE")
            other.execute("ROLLBACK")
            self.assertEqual(self.authority.freeze(expected_epoch=1), 2)
        finally:
            other.close()

    def test_incorrect_tenant_operation_and_generation_rejected(self):
        cases = (
            {"expected_epoch": True, "operation_id": A, "tenant": T,
             "marker": "canary_good"},
            {"expected_epoch": 0, "operation_id": A, "tenant": T,
             "marker": "canary_good"},
            {"expected_epoch": 1, "operation_id": "short", "tenant": T,
             "marker": "canary_good"},
            {"expected_epoch": 1, "operation_id": A, "tenant": "customer",
             "marker": "canary_good"},
            {"expected_epoch": 1, "operation_id": A, "tenant": T,
             "marker": "sensitive customer data"},
        )
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    self.authority.write_canary(**kwargs)
        self.assertEqual(self.authority.state()["synthetic_committed_writes"], 0)

    def test_disable_gate_rejects_every_mutation(self):
        with patch.dict(os.environ, {"BAM_EPHEMERAL_PG_TEST": "0"}):
            with self.assertRaises(PermissionError):
                self.write(1)
            with self.assertRaises(PermissionError):
                self.authority.freeze(expected_epoch=1)
            with self.assertRaises(PermissionError):
                self.authority.resume(expected_epoch=1)
            with self.assertRaises(PermissionError):
                self.authority.state()
        self.assertEqual(self.authority.state()["epoch"], 1)


if __name__ == "__main__":
    unittest.main()
