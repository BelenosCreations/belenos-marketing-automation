import os
import sqlite3
import unittest
from contextlib import closing
from unittest.mock import patch

from neon_disposable_split_commit_rehearsal import DisposableSplitCommitRehearsal


OPERATION = "a" * 32
TENANT = "ci_tenant_a"
MARKER = "canary_draft"


class SplitCommitRehearsalTests(unittest.TestCase):
    def setUp(self):
        gate = patch.dict(os.environ, {"BAM_EPHEMERAL_PG_TEST": "1"})
        gate.start()
        self.addCleanup(gate.stop)
        self.rehearsal = DisposableSplitCommitRehearsal()
        self.addCleanup(self.rehearsal.close)
        self.rehearsal.claim(expected_epoch=1, operation_id=OPERATION, tenant=TENANT)

    def _persist(self, epoch=1):
        self.rehearsal.commit_output(
            expected_epoch=epoch, operation_id=OPERATION, tenant=TENANT, marker=MARKER)

    def _finalize(self, epoch=1):
        return self.rehearsal.finalize(
            expected_epoch=epoch, operation_id=OPERATION, tenant=TENANT)

    def _recover(self, epoch=3, tenant=TENANT):
        return self.rehearsal.reconcile_committed_output(
            expected_epoch=epoch, operation_id=OPERATION, tenant=tenant)

    def _rows(self):
        db = self.rehearsal._db
        return (
            db.execute("SELECT generation, completed FROM ci_draft_requests").fetchall(),
            db.execute("SELECT generation, marker FROM ci_draft_outputs").fetchall(),
        )

    def _freeze_and_reopen(self):
        self.assertEqual(self.rehearsal.freeze(expected_epoch=1), 2)
        self.rehearsal.reopen()
        self.assertEqual(self.rehearsal.resume(expected_epoch=2), 3)

    def test_normal_finalize_is_idempotent_after_lost_acknowledgement(self):
        self._persist()
        self.assertTrue(self._finalize())
        self.rehearsal.reopen()
        self.assertFalse(self._finalize())
        with self.assertRaises(PermissionError):
            self._persist()
        self.assertEqual(self._rows(), ([(1, 1)], [(1, MARKER)]))

    def test_prior_output_is_reconciled_without_rewriting_after_freeze(self):
        self._persist()
        self.assertEqual(self.rehearsal.freeze(expected_epoch=1), 2)
        self.rehearsal.reopen()
        with self.assertRaises(PermissionError):
            self._recover(epoch=2)
        self.assertEqual(self.rehearsal.resume(expected_epoch=2), 3)
        for epoch in (1, 3):
            with self.assertRaises(PermissionError):
                self._finalize(epoch)
            with self.assertRaises(PermissionError):
                self._persist(epoch)
        with self.assertRaises(PermissionError):
            self.rehearsal.claim(expected_epoch=3, operation_id=OPERATION, tenant=TENANT)
        with self.assertRaises(PermissionError):
            self._recover(tenant="ci_tenant_b")
        self.assertEqual(self._rows(), ([(1, 0)], [(1, MARKER)]))
        self.assertTrue(self._recover())
        self.rehearsal.reopen()
        self.assertFalse(self._recover())
        self.assertEqual(self._rows(), ([(1, 1)], [(1, MARKER)]))

    def test_uncommitted_output_rolls_back_and_cannot_be_reconciled(self):
        # Abandon a transaction after the insert, before COMMIT.
        db = self.rehearsal._db
        db.execute("BEGIN IMMEDIATE")
        db.execute("INSERT INTO ci_draft_outputs VALUES (?, ?, 1, ?)",
                   (OPERATION, TENANT, MARKER))
        self.rehearsal.reopen()
        self._freeze_and_reopen()
        with self.assertRaises(PermissionError):
            self._recover()
        with self.assertRaises(PermissionError):
            self._persist(3)
        self.assertEqual(self._rows(), ([(1, 0)], []))

    def test_mismatched_receipt_fails_closed(self):
        self._persist()
        self._freeze_and_reopen()
        self.rehearsal._db.execute("UPDATE ci_draft_outputs SET generation=3")
        with self.assertRaises(PermissionError):
            self._recover()
        self.assertEqual(self._rows(), ([(1, 0)], [(3, MARKER)]))

    def test_recovery_cannot_replace_normal_finalization_or_bypass_ci_gate(self):
        self._persist()
        with self.assertRaises(PermissionError):
            self._recover(epoch=1)
        with patch.dict(os.environ, {"BAM_EPHEMERAL_PG_TEST": "0"}):
            with self.assertRaises(PermissionError):
                self._finalize()
            with self.assertRaises(PermissionError):
                self._recover()
            with self.assertRaises(PermissionError):
                DisposableSplitCommitRehearsal()
        self.assertEqual(self._rows(), ([(1, 0)], [(1, MARKER)]))

    def test_freeze_cannot_take_the_writer_lock_before_output_commit(self):
        with closing(self.rehearsal._connect()) as competitor:
            with self.rehearsal._admitted_transaction(1):
                self.rehearsal._db.execute(
                    "INSERT INTO ci_draft_outputs VALUES (?, ?, 1, ?)",
                    (OPERATION, TENANT, MARKER),
                )
                with self.assertRaisesRegex(sqlite3.OperationalError, "locked"):
                    competitor.execute("BEGIN IMMEDIATE")
        self._freeze_and_reopen()
        self.assertTrue(self._recover())
        self.assertEqual(self._rows(), ([(1, 1)], [(1, MARKER)]))
