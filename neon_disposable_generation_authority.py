"""Disposable, CI-only *transaction-bound* generation fencing model.

This is intentionally not called by BAM routes or services. The SQLite file
is destroyed with its fixture. No independent generation custody, operator
identity, tenant authentication, production writer integration or PG cutover
is provided. A successful test only establishes local SQLite lock ordering.
"""
import os
import re
import sqlite3
import stat
import tempfile
from pathlib import Path

_EPOCH_LIMIT = 2147483647
_ID = re.compile(r"[0-9a-f]{32}\Z")
_TENANT = re.compile(r"ci_tenant_[a-z]{1,12}\Z")
_CANARY = re.compile(r"canary_[a-z0-9]{1,24}\Z")
_SCHEMA = """
CREATE TABLE ci_generation (
  id INTEGER PRIMARY KEY CHECK(id=1),
  epoch INTEGER NOT NULL CHECK(epoch>0), mode TEXT NOT NULL
);
CREATE TABLE ci_writes (
  operation_id TEXT PRIMARY KEY,
  tenant TEXT NOT NULL, epoch INTEGER NOT NULL, marker TEXT NOT NULL
);
INSERT INTO ci_generation(id,epoch,mode) VALUES(1,1,'open');
"""


def _gate():
    if os.environ.get("BAM_EPHEMERAL_PG_TEST") != "1":
        raise PermissionError("Generation fixture is not a production fence")


def _epoch(value):
    if type(value) is not int or not 1 <= value <= _EPOCH_LIMIT:
        raise ValueError("Invalid bounded CI generation")


def _matches(value, regex, label):
    if type(value) is not str or not regex.fullmatch(value):
        raise ValueError("Invalid synthetic " + label)


class _DisposableGenerationAuthority:
    """One private ephemeral SQLite fixture, never mounted into BAM."""

    def __init__(self):
        _gate()
        self._temporary = tempfile.TemporaryDirectory(prefix="bam_ci_generation_")
        self._path = Path(self._temporary.name) / "authority.sqlite3"
        self._db = None
        try:
            descriptor = os.open(self._path, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                                 | getattr(os, "O_NOFOLLOW", 0), 0o600)
            os.close(descriptor)
            self._db = self._connect()
            self._db.executescript(_SCHEMA)
        except BaseException:
            self.close()
            raise

    def _connect(self):
        _gate()
        d = self._path.parent.lstat()
        f = self._path.lstat()
        if (not stat.S_ISDIR(d.st_mode) or d.st_mode & 0o077
                or not stat.S_ISREG(f.st_mode) or f.st_mode & 0o077
                or f.st_nlink != 1):
            raise PermissionError("Unsafe disposable generation fixture")
        db = sqlite3.connect(str(self._path), timeout=0, isolation_level=None)
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA synchronous=FULL")
        return db

    def close_connection(self):
        if self._db is not None:
            self._db.close()
            self._db = None

    def reopen(self):
        _gate()
        self.close_connection()
        self._db = self._connect()

    def close(self):
        self.close_connection()
        self._temporary.cleanup()

    def __enter__(self):
        _gate()
        return self

    def __exit__(self, _type, _value, _tb):
        self.close()

    def state(self):
        _gate()
        epoch, mode = self._db.execute(
            "SELECT epoch,mode FROM ci_generation WHERE id=1").fetchone()
        count = self._db.execute("SELECT COUNT(*) FROM ci_writes").fetchone()[0]
        return {
            "epoch": epoch, "mode": mode, "synthetic_committed_writes": count,
            "persistent_production_authority": False,
            "application_writers_fenced": False,
            "independently_authenticated_operator": False,
            "postgres_connection_attempted": False,
            "customer_data_read": False, "cutover_permitted": False,
            "production_ready": False, "publishing_enabled": False,
        }

    def _transition(self, expected_epoch, current_mode, next_mode):
        _gate()
        _epoch(expected_epoch)
        self._db.execute("BEGIN IMMEDIATE")
        try:
            epoch, mode = self._db.execute(
                "SELECT epoch,mode FROM ci_generation WHERE id=1").fetchone()
            if epoch != expected_epoch or mode != current_mode:
                raise PermissionError("Stale generation or invalid mode transition")
            if epoch == _EPOCH_LIMIT:
                raise PermissionError("Generation exhausted; fail closed")
            update = self._db.execute(
                "UPDATE ci_generation SET epoch=?,mode=?"
                " WHERE id=1 AND epoch=? AND mode=?",
                (epoch + 1, next_mode, epoch, current_mode))
            if update.rowcount != 1:
                raise PermissionError("Atomic generation CAS failed")
            self._db.execute("COMMIT")
            return epoch + 1
        except BaseException:
            self._db.execute("ROLLBACK")
            raise

    def freeze(self, *, expected_epoch):
        """Advance and freeze; already admitted transactions serialize first."""
        return self._transition(expected_epoch, "open", "frozen")

    def resume(self, *, expected_epoch):
        """Advance again; never reopen old generation after a freeze."""
        return self._transition(expected_epoch, "frozen", "open")

    def write_canary(self, *, expected_epoch, operation_id, tenant, marker):
        """Check epoch INSIDE the same SQLite write transaction as the insert."""
        _gate()
        _epoch(expected_epoch)
        _matches(operation_id, _ID, "operation")
        _matches(tenant, _TENANT, "tenant")
        _matches(marker, _CANARY, "marker")
        self._db.execute("BEGIN IMMEDIATE")
        try:
            epoch, mode = self._db.execute(
                "SELECT epoch,mode FROM ci_generation WHERE id=1").fetchone()
            if epoch != expected_epoch or mode != "open":
                raise PermissionError("Stale or frozen synthetic writer")
            try:
                self._db.execute(
                    "INSERT INTO ci_writes(operation_id,tenant,epoch,marker)"
                    " VALUES(?,?,?,?)",
                    (operation_id, tenant, epoch, marker))
            except sqlite3.IntegrityError as exc:
                raise PermissionError("Replayed operation ID across generations") from exc
            self._db.execute("COMMIT")
            return {"accepted": True, "epoch": epoch,
                    "tenant": tenant, "operation_id": operation_id,
                    "production_write": False}
        except BaseException:
            self._db.execute("ROLLBACK")
            raise
