"""Offline session store prototype.

Only the server creates sessions. Token values are never stored in plaintext.
Authentication of the person presenting credentials is outside this module.
"""
import hashlib
import secrets
import sqlite3
import time
from dataclasses import dataclass

from access_policy import Principal, Role


@dataclass(frozen=True)
class Session:
    principal: Principal
    expires_at: int


class SessionStore:
    def __init__(self, connection: sqlite3.Connection):
        self.db = connection
        self.db.execute("""CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY,
            subject_id TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            role TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            revoked_at INTEGER
        )""")
        self.db.commit()

    @staticmethod
    def _digest(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def issue(self, principal: Principal, *, ttl_seconds: int = 3600, now: int | None = None) -> str:
        """Caller MUST authenticate and authorize principal before issuing."""
        if not principal.active or not principal.subject_id or not principal.tenant_id:
            raise ValueError("Active authenticated identity required")
        try:
            role = Role(principal.role)
        except (ValueError, TypeError) as exc:
            raise ValueError("Unknown role") from exc
        if not isinstance(ttl_seconds, int) or isinstance(ttl_seconds, bool) or not 1 <= ttl_seconds <= 86400:
            raise ValueError("TTL must be between 1 and 86400 seconds")
        timestamp = int(time.time()) if now is None else now
        token = secrets.token_urlsafe(32)
        self.db.execute(
            "INSERT INTO sessions (token_hash, subject_id, tenant_id, role, expires_at) VALUES (?, ?, ?, ?, ?)",
            (self._digest(token), principal.subject_id, principal.tenant_id, role.value, timestamp + ttl_seconds),
        )
        self.db.commit()
        return token

    def resolve(self, token: str, *, now: int | None = None) -> Session | None:
        if not isinstance(token, str) or not token:
            return None
        timestamp = int(time.time()) if now is None else now
        row = self.db.execute(
            """SELECT subject_id, tenant_id, role, expires_at
               FROM sessions WHERE token_hash = ? AND revoked_at IS NULL AND expires_at > ?""",
            (self._digest(token), timestamp),
        ).fetchone()
        if row is None:
            return None
        subject_id, tenant_id, role, expires_at = row
        try:
            verified_role = Role(role)
        except ValueError:
            return None
        return Session(Principal(subject_id, tenant_id, verified_role), expires_at)

    def revoke(self, token: str, *, now: int | None = None) -> None:
        if not isinstance(token, str) or not token:
            return
        timestamp = int(time.time()) if now is None else now
        self.db.execute(
            "UPDATE sessions SET revoked_at = ? WHERE token_hash = ? AND revoked_at IS NULL",
            (timestamp, self._digest(token)),
        )
        self.db.commit()

    def revoke_subject(self, tenant_id: str, subject_id: str, *, now: int | None = None) -> int:
        """Invalidate all sessions when employee access is removed or changed."""
        timestamp = int(time.time()) if now is None else now
        cursor = self.db.execute(
            """UPDATE sessions SET revoked_at = ?
               WHERE tenant_id = ? AND subject_id = ? AND revoked_at IS NULL""",
            (timestamp, tenant_id, subject_id),
        )
        self.db.commit()
        return cursor.rowcount

    def revoke_identity(self, subject_id: str, *, now: int | None = None) -> int:
        """Revoke every BAM session for one identity across all businesses.

        Trusted administrative action only; callers must authenticate and
        authorize the identity-level revocation before invoking this method.
        """
        if not isinstance(subject_id, str) or not subject_id.strip():
            raise ValueError("Subject required")
        timestamp = int(time.time()) if now is None else now
        if type(timestamp) is not int or timestamp < 0:
            raise ValueError("Invalid revocation time")
        cursor = self.db.execute(
            """UPDATE sessions SET revoked_at=?
               WHERE subject_id=? AND revoked_at IS NULL""",
            (timestamp, subject_id),
        )
        self.db.commit()
        return cursor.rowcount

    def resolve_current(self, token: str, *, directory, now: int | None = None) -> Session | None:
        """Resolve a session against current tenant membership and role.

        Fail closed on removed members or stale roles. Unlike resolve(), this
        must be used at privileged API boundaries requiring fresh permissions.
        """
        session = self.resolve(token, now=now)
        if session is None:
            return None
        current = directory.resolve(session.principal.tenant_id, session.principal.subject_id)
        if current is None or current.role != session.principal.role:
            return None
        return Session(current, session.expires_at)
