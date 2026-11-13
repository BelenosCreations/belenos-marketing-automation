"""Disposable v1 migration transaction protocol rehearsal — never a PG runner.

Isolated SQLite shared-memory canaries only. This does NOT fence any BAM worker,
authenticate an operator, verify an external journal head, open customer storage,
connect to PostgreSQL, or authorize stage 08/production promotion.
"""
import hashlib
import json
import os
import re
import sqlite3

_HEX32 = re.compile(r"[0-9a-f]{32}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")


def _hash(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")).hexdigest()


def _validate_context(operation_id, journal_head, fence_token, epoch, version):
    if os.environ.get("BAM_EPHEMERAL_PG_TEST") != "1":
        raise PermissionError("Disposable protocol disabled outside explicit CI")
    if type(operation_id) is not str or not _HEX32.fullmatch(operation_id):
        raise ValueError("Externally allocated opaque operation ID required")
    if type(journal_head) is not str or not _HEX64.fullmatch(journal_head):
        raise ValueError("Independent intent-head SHA-256 syntax required")
    if type(fence_token) is not str or not _HEX32.fullmatch(fence_token):
        raise ValueError("Opaque synthetic fence token required")
    if type(epoch) is not int or not 1 <= epoch <= 2147483647:
        raise ValueError("Positive bounded synthetic fence epoch required")
    if type(version) is not int or version != 1:
        raise PermissionError("Only inactive protocol version 1 permitted")


class _DisposableProtocol:
    """Not exported to the application. Only synthetic in-memory connections."""

    def __init__(self, *, operation_id, journal_head, fence_token, epoch,
                 version=1):
        _validate_context(operation_id, journal_head, fence_token,
                          epoch, version)
        self.operation_id = operation_id
        self.journal_head = journal_head
        self.fence_token = fence_token
        self.epoch = epoch
        self.version = version
        uri = ("file:bam_ci_migration_protocol_" + os.urandom(16).hex()
               + "?mode=memory&cache=shared")
        self.owner = sqlite3.connect(uri, uri=True, isolation_level=None,
                                     timeout=0)
        try:
            self.contender = sqlite3.connect(uri, uri=True,
                                             isolation_level=None, timeout=0)
            self.owner.execute("""CREATE TABLE ci_protocol (
                operation_id TEXT PRIMARY KEY, version INTEGER NOT NULL,
                intent_head TEXT NOT NULL, fence_token TEXT NOT NULL,
                epoch INTEGER NOT NULL, stage INTEGER NOT NULL,
                event_head TEXT NOT NULL, status TEXT NOT NULL
            )""")
            self.owner.execute("""CREATE TABLE ci_protocol_events (
                operation_id TEXT NOT NULL, sequence INTEGER NOT NULL,
                previous_head TEXT NOT NULL, event_head TEXT NOT NULL,
                PRIMARY KEY(operation_id, sequence)
            )""")
            self.owner.execute("""CREATE TABLE ci_synthetic_payload (
                id INTEGER PRIMARY KEY, marker TEXT NOT NULL
            )""")
        except BaseException:
            self.owner.close()
            if hasattr(self, "contender"):
                self.contender.close()
            raise

    def close(self):
        if self.owner is not None:
            self.owner.close()
            self.owner = None
        self.contender.close()

    def _context(self):
        return dict(operation_id=self.operation_id,
                    version=self.version, intent_head=self.journal_head,
                    fence_token=self.fence_token, epoch=self.epoch)

    def _transaction(self, connection, callback):
        connection.execute("BEGIN IMMEDIATE")
        try:
            value = callback(connection)
            connection.execute("COMMIT")
            return value
        except BaseException:
            connection.execute("ROLLBACK")
            raise

    def reserve(self, connection=None):
        """A committed unique ID cannot be reserved again in this fixture."""
        db = self.owner if connection is None else connection
        genesis = _hash({"format": "bam-ci-protocol-v1", **self._context()})

        def action(conn):
            try:
                conn.execute("""INSERT INTO ci_protocol VALUES(
                    ?,1,?,?,?,0,?,'reserved')""", (
                    self.operation_id, self.journal_head, self.fence_token,
                    self.epoch, genesis))
            except sqlite3.IntegrityError as exc:
                raise PermissionError("Operation replay in disposable ledger") from exc
            return genesis

        return self._transaction(db, action)

    def advance(self, sequence, *, epoch=None, fence_token=None,
                journal_head=None, connection=None):
        """CAS an exactly-next stage and atomic receipt, never stage 08."""
        if type(sequence) is not int or not 1 <= sequence <= 7:
            raise PermissionError("Skipped, malformed, or promotion stage")
        db = self.owner if connection is None else connection
        provided_epoch = self.epoch if epoch is None else epoch
        provided_token = self.fence_token if fence_token is None else fence_token
        provided_head = self.journal_head if journal_head is None else journal_head

        def action(conn):
            row = conn.execute("""SELECT version,intent_head,fence_token,
                epoch,stage,event_head,status FROM ci_protocol
                WHERE operation_id=?""", (self.operation_id,)).fetchone()
            if row is None or row[0] != 1 or row[1] != provided_head or (
                    row[2] != provided_token or type(provided_token) is not str
                    or row[3] != provided_epoch or type(provided_epoch) is not int
                    or row[4] != sequence - 1 or row[6] != "reserved"):
                raise PermissionError("Stale writer, conflicting head, or step replay")
            next_head = _hash({
                "format": "bam-ci-protocol-event-v1",
                "operation_id": self.operation_id,
                "version": 1, "intent_head": self.journal_head,
                "epoch": self.epoch, "sequence": sequence,
                "previous_head": row[5],
            })
            conn.execute("""INSERT INTO ci_protocol_events
                VALUES(?,?,?,?)""", (
                self.operation_id, sequence, row[5], next_head))
            updated = conn.execute("""UPDATE ci_protocol
                SET stage=?,event_head=? WHERE operation_id=?
                AND stage=? AND event_head=? AND status='reserved'""",
                (sequence, next_head, self.operation_id,
                 sequence - 1, row[5])).rowcount
            if updated != 1:
                raise PermissionError("Atomic stage compare-and-swap failed")
            return next_head

        return self._transaction(db, action)

    def abandon(self, *, connection=None):
        """Terminal abort, not restoration or production rollback."""
        db = self.owner if connection is None else connection

        def action(conn):
            updated = conn.execute("""UPDATE ci_protocol SET status='aborted'
                WHERE operation_id=? AND version=1 AND intent_head=?
                AND fence_token=? AND epoch=? AND status='reserved'""",
                (self.operation_id, self.journal_head, self.fence_token,
                 self.epoch)).rowcount
            if updated != 1:
                raise PermissionError("Cannot abort stale or terminal operation")
            return True

        return self._transaction(db, action)

    def inspect_chain(self):
        """Check internal consistency, NOT authenticity or external custody."""
        rows = self.contender.execute("""SELECT sequence,previous_head,event_head
            FROM ci_protocol_events WHERE operation_id=? ORDER BY sequence""",
            (self.operation_id,)).fetchall()
        previous = _hash({"format": "bam-ci-protocol-v1", **self._context()})
        for expected, (seq, old, current) in enumerate(rows, 1):
            if type(seq) is not int or seq != expected or old != previous:
                raise PermissionError("Synthetic chain order or predecessor drift")
            proposed = _hash({
                "format": "bam-ci-protocol-event-v1",
                "operation_id": self.operation_id, "version": 1,
                "intent_head": self.journal_head, "epoch": self.epoch,
                "sequence": seq, "previous_head": old,
            })
            if current != proposed:
                raise PermissionError("Synthetic receipt corruption")
            previous = current
        row = self.contender.execute("""SELECT stage,event_head,status
            FROM ci_protocol WHERE operation_id=?""",
            (self.operation_id,)).fetchone()
        if not row or row[0] != len(rows) or row[1] != previous:
            raise PermissionError("Synthetic stage/head mismatch")
        return {"stage": row[0], "head_sha256": previous,
                "status": row[2], "event_count": len(rows)}


def rehearse_disposable_versioned_protocol(*, operation_id, journal_head,
                                            fence_token, epoch,
                                            release_mode="rollback",
                                            version=1):
    """Exercise v1 steps and loss of uncommitted canary, no app integration."""
    _validate_context(operation_id, journal_head, fence_token, epoch, version)
    if release_mode not in ("rollback", "abandoned_connection"):
        raise ValueError("Unrecognized synthetic rollback scenario")
    protocol = _DisposableProtocol(
        operation_id=operation_id, journal_head=journal_head,
        fence_token=fence_token, epoch=epoch, version=version)
    try:
        protocol.reserve()
        for number in range(1, 8):
            protocol.advance(number)
        checked = protocol.inspect_chain()
        protocol.owner.execute("BEGIN IMMEDIATE")
        protocol.owner.execute("""INSERT INTO ci_synthetic_payload
            VALUES(1,'discard_on_rollback')""")
        try:
            protocol.contender.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError:
            competitor_blocked = True
        else:
            protocol.contender.execute("ROLLBACK")
            raise AssertionError("Competing synthetic writer unexpectedly entered")
        if release_mode == "rollback":
            protocol.owner.execute("ROLLBACK")
        else:
            protocol.owner.close()
            protocol.owner = None
        protocol.abandon(connection=protocol.contender)
        if protocol.contender.execute(
                "SELECT COUNT(*) FROM ci_synthetic_payload").fetchone()[0] != 0:
            raise AssertionError("Uncommitted synthetic payload survived")
        if protocol.inspect_chain()["status"] != "aborted":
            raise AssertionError("Synthetic operation was not terminal")
        return {
            "status": "ci_only_versioned_protocol_rehearsed",
            "version": 1, "release_mode": release_mode,
            "operation_id": operation_id,
            "synthetic_stages_exercised": checked["event_count"],
            "synthetic_receipt_head_sha256": checked["head_sha256"],
            "synthetic_competing_writer_blocked": competitor_blocked,
            "synthetic_payload_rolled_back": True,
            "operation_terminally_aborted": True,
            "one_fixture_only_replay_guard": True,
            "external_head_authenticity_verified": False,
            "persistent_replay_authority_implemented": False,
            "independent_operator_approval_proven": False,
            "application_writers_fenced": False,
            "background_workers_fenced": False,
            "postgres_connected": False, "postgres_transaction_started": False,
            "customer_database_opened": False, "customer_rows_read": False,
            "production_restore_rehearsed": False,
            "promotion_authorized": False, "cutover_permitted": False,
            "publishing_enabled": False, "production_ready": False,
        }
    finally:
        protocol.close()
