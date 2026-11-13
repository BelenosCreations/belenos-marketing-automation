"""CI-only disposable durable SQLite replay-ledger rehearsal, never production.

Creates its own private disposable database, not a supplied customer DB. HMAC
authenticates synthetic event chains against an EXTERNALLY SUPPLIED latest-head
pin. A caller-provided pin is not proof of independent custody or approval.
No migration, PostgreSQL, publishing, external storage, or stage 08 exists.
"""
import hashlib
import hmac
import json
import os
import re
import sqlite3
import stat
import tempfile

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[0-9a-f]{32}\Z")
_GENESIS = "0" * 64
_FIELDS = ("sequence", "operation_id", "action", "stage", "epoch",
           "intent_head", "fence_sha256", "previous_mac")
_SCHEMA = """
CREATE TABLE ci_meta(
 id INTEGER PRIMARY KEY CHECK(id=1),
 sequence INTEGER NOT NULL, head TEXT NOT NULL, last_epoch INTEGER NOT NULL
);
CREATE TABLE ci_operations(
 operation_id TEXT PRIMARY KEY, intent_head TEXT NOT NULL,
 epoch INTEGER NOT NULL, fence_sha256 TEXT NOT NULL,
 stage INTEGER NOT NULL, status TEXT NOT NULL
);
CREATE TABLE ci_events(
 sequence INTEGER PRIMARY KEY, operation_id TEXT NOT NULL,
 action TEXT NOT NULL, stage INTEGER NOT NULL, epoch INTEGER NOT NULL,
 intent_head TEXT NOT NULL, fence_sha256 TEXT NOT NULL,
 previous_mac TEXT NOT NULL, mac TEXT NOT NULL
);
INSERT INTO ci_meta VALUES(1,0,'""" + _GENESIS + """',0);
"""


def _gate():
    if os.environ.get("BAM_EPHEMERAL_PG_TEST") != "1":
        raise PermissionError("CI-only disposable replay ledger is disabled")


def _hex(value, expression, name):
    if type(value) is not str or expression.fullmatch(value) is None:
        raise ValueError("Invalid synthetic " + name)


def _epoch(value):
    if type(value) is not int or not 1 <= value <= 2147483647:
        raise ValueError("Invalid positive bounded synthetic epoch")


def _mac(key, item):
    payload = json.dumps(item, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True).encode("ascii")
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def _fence(token):
    _hex(token, _ID, "fence token")
    return hashlib.sha256(token.encode("ascii")).hexdigest()


class _DisposableDurableReplayLedger:
    """Strictly private, automatically destroyed CI test fixture."""

    def __init__(self, *, signing_key):
        _gate()
        if type(signing_key) is not bytes or len(signing_key) < 32:
            raise ValueError("Externally provided synthetic HMAC key required")
        self._key = signing_key
        self._temporary = tempfile.TemporaryDirectory(prefix="bam_ci_replay_")
        self._path = os.path.join(self._temporary.name, "replay.sqlite3")
        self._db = None
        try:
            fd = os.open(self._path, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                         | getattr(os, "O_NOFOLLOW", 0), 0o600)
            os.close(fd)
            self._db = self._connect()
            self._db.executescript(_SCHEMA)
        except BaseException:
            self.close()
            raise

    def _connect(self):
        _gate()
        parent = os.lstat(self._temporary.name)
        inode = os.lstat(self._path)
        if (not stat.S_ISDIR(parent.st_mode) or parent.st_mode & 0o077
                or not stat.S_ISREG(inode.st_mode) or inode.st_mode & 0o077
                or inode.st_nlink != 1):
            raise PermissionError("Unsafe disposable SQLite file or directory")
        db = sqlite3.connect(self._path, isolation_level=None, timeout=0)
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def close_connection(self):
        if self._db is not None:
            self._db.close()
            self._db = None

    def reopen(self):
        """Simulate another process reopening the same private fixture."""
        _gate()
        self.close_connection()
        self._db = self._connect()

    def close(self):
        self.close_connection()
        self._temporary.cleanup()

    def _verify(self, expected_head):
        _hex(expected_head, _SHA, "independent latest head")
        db = self._db
        rows = db.execute("""SELECT sequence,operation_id,action,stage,epoch,
            intent_head,fence_sha256,previous_mac,mac
            FROM ci_events ORDER BY sequence""").fetchall()
        previous = _GENESIS
        state = {}
        latest_epoch = 0
        for number, row in enumerate(rows, 1):
            record = dict(zip(_FIELDS, row[:8]))
            if record["sequence"] != number or record["previous_mac"] != previous:
                raise PermissionError("Replay-ledger ordering or predecessor tampering")
            if not hmac.compare_digest(_mac(self._key, record), row[8]):
                raise PermissionError("Replay-ledger event HMAC mismatch")
            operation = record["operation_id"]
            action = record["action"]
            stage = record["stage"]
            epoch = record["epoch"]
            identity = (record["intent_head"], epoch, record["fence_sha256"])
            if action == "reserve":
                if (operation in state or stage != 0 or
                        type(epoch) is not int or epoch <= latest_epoch or
                        any(item[4] == "reserved" for item in state.values())):
                    raise PermissionError("Replay-ledger reservation history invalid")
                latest_epoch = epoch
                state[operation] = (*identity, 0, "reserved")
            else:
                prior = state.get(operation)
                if (prior is None or prior[:3] != identity
                        or prior[4] != "reserved"):
                    raise PermissionError("Replay-ledger operation context drift")
                if action == "advance" and type(stage) is int and (
                        1 <= stage <= 7 and stage == prior[3] + 1):
                    state[operation] = (*identity, stage, "reserved")
                elif action == "abort" and stage == prior[3]:
                    state[operation] = (*identity, stage, "aborted")
                else:
                    raise PermissionError("Replay-ledger stage or terminal tampering")
            previous = row[8]
        meta = db.execute(
            "SELECT sequence,head,last_epoch FROM ci_meta WHERE id=1").fetchone()
        if (meta != (len(rows), previous, latest_epoch) or
                not hmac.compare_digest(previous, expected_head)):
            raise PermissionError("Independent latest-head or SQLite metadata mismatch")
        database_state = {
            row[0]: (row[1], row[2], row[3], row[4], row[5])
            for row in db.execute("""SELECT operation_id,intent_head,epoch,
                fence_sha256,stage,status FROM ci_operations""")
        }
        if database_state != state:
            raise PermissionError("Unsigned operation-state mismatch")
        return (len(rows), previous, latest_epoch, state)

    def inspect(self, *, independently_pinned_head):
        """Verify all receipts, derived state and independent pin, no writes."""
        _gate()
        count, head, epoch, operations = self._verify(independently_pinned_head)
        return {"synthetic_receipts": count, "verified_head_sha256": head,
                "last_epoch": epoch,
                "synthetic_operations": len(operations),
                "independent_pin_matches": True,
                "external_head_custody_proven": False,
                "operator_approval_proven": False,
                "customer_database_opened": False,
                "production_ready": False}

    def _apply(self, action, *, operation_id, intent_head, fence_token,
               epoch, independently_pinned_head, stage=None):
        _gate()
        _hex(operation_id, _ID, "operation ID")
        _hex(intent_head, _SHA, "intent chain head")
        fence_sha = _fence(fence_token)
        _epoch(epoch)
        if action == "advance":
            if type(stage) is not int or not 1 <= stage <= 7:
                raise PermissionError("Stage must be exactly 01..07; no promotion")
        elif action not in ("reserve", "abort") or stage is not None:
            raise ValueError("Unknown synthetic transition")
        db = self._db
        db.execute("BEGIN IMMEDIATE")
        try:
            seq, previous, last_epoch, operations = self._verify(
                independently_pinned_head)
            identity = (intent_head, epoch, fence_sha)
            prior = operations.get(operation_id)
            if action == "reserve":
                if (prior is not None or epoch <= last_epoch
                        or any(item[4] == "reserved" for item in operations.values())):
                    raise PermissionError("Duplicate operation or stale fence epoch")
                new_stage = 0
                db.execute("""INSERT INTO ci_operations VALUES(?,?,?,?,?,'reserved')""",
                           (operation_id, *identity, new_stage))
                last_epoch = epoch
            else:
                if prior is None or prior[:3] != identity or prior[4] != "reserved":
                    raise PermissionError("Stale, foreign or aborted operation")
                new_stage = prior[3] if action == "abort" else stage
                if action == "advance" and new_stage != prior[3] + 1:
                    raise PermissionError("Skipped or replayed transaction stage")
                status = "aborted" if action == "abort" else "reserved"
                updated = db.execute("""UPDATE ci_operations
                    SET stage=?,status=? WHERE operation_id=?
                    AND stage=? AND status='reserved'""",
                    (new_stage, status, operation_id, prior[3])).rowcount
                if updated != 1:
                    raise PermissionError("Atomic operation CAS failed")
            record = dict(sequence=seq + 1, operation_id=operation_id,
                          action=action, stage=new_stage, epoch=epoch,
                          intent_head=intent_head, fence_sha256=fence_sha,
                          previous_mac=previous)
            head = _mac(self._key, record)
            db.execute("""INSERT INTO ci_events VALUES(?,?,?,?,?,?,?,?,?)""",
                       tuple(record[name] for name in _FIELDS) + (head,))
            db.execute("""UPDATE ci_meta SET sequence=?,head=?,last_epoch=?
                WHERE id=1""", (seq + 1, head, last_epoch))
            db.execute("COMMIT")
            return head
        except BaseException:
            db.execute("ROLLBACK")
            raise

    def reserve(self, *, operation_id, intent_head, fence_token, epoch,
                independently_pinned_head):
        return self._apply("reserve", operation_id=operation_id,
                           intent_head=intent_head, fence_token=fence_token,
                           epoch=epoch,
                           independently_pinned_head=independently_pinned_head)

    def advance(self, *, operation_id, intent_head, fence_token, epoch,
                stage, independently_pinned_head):
        return self._apply("advance", operation_id=operation_id,
                           intent_head=intent_head, fence_token=fence_token,
                           epoch=epoch, stage=stage,
                           independently_pinned_head=independently_pinned_head)

    def abort(self, *, operation_id, intent_head, fence_token, epoch,
              independently_pinned_head):
        return self._apply("abort", operation_id=operation_id,
                           intent_head=intent_head, fence_token=fence_token,
                           epoch=epoch,
                           independently_pinned_head=independently_pinned_head)


def rehearse_disposable_durable_replay(*, signing_key, operation_id,
                                      intent_head, fence_token, epoch):
    """Demonstrate private-file persistence across reconnect, then deletion."""
    _gate()
    ledger = _DisposableDurableReplayLedger(signing_key=signing_key)
    try:
        args = dict(operation_id=operation_id, intent_head=intent_head,
                    fence_token=fence_token, epoch=epoch)
        head = ledger.reserve(**args, independently_pinned_head=_GENESIS)
        ledger.reopen()
        for stage in range(1, 8):
            head = ledger.advance(**args, stage=stage,
                                  independently_pinned_head=head)
        ledger.reopen()
        checked = ledger.inspect(independently_pinned_head=head)
        head = ledger.abort(**args, independently_pinned_head=head)
        final = ledger.inspect(independently_pinned_head=head)
        return {
            "status": "ci_disposable_durable_replay_rehearsed_only",
            "receipt_count_after_abort": final["synthetic_receipts"],
            "synthetic_state_persisted_across_reconnect": True,
            "event_chain_verified_against_caller_pin": True,
            "terminal_abort_recorded": True,
            "external_latest_head_authority_verified": False,
            "independent_signing_key_custody_verified": False,
            "genuine_application_writer_fence": False,
            "postgres_connected": False,
            "customer_database_opened": False,
            "customer_rows_read": False,
            "migration_executed": False,
            "production_rollback_rehearsed": False,
            "cutover_permitted": False,
            "production_ready": False,
            "publishing_enabled": False,
        }
    finally:
        ledger.close()
