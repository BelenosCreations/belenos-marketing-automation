"""Tenant-scoped account directory prototype; no registration or authentication.

Provisioning is an administrator-controlled server action. Do not expose this
class directly to untrusted mobile clients. Identity verification is separate.
"""
import sqlite3
from access_policy import Action, Principal, Resource, Role, require_permission


class AccountDirectory:
    def __init__(self, db: sqlite3.Connection):
        self.db = db
        self.db.execute("""CREATE TABLE IF NOT EXISTS members (
            tenant_id TEXT NOT NULL,
            subject_id TEXT NOT NULL,
            role TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (tenant_id, subject_id)
        )""")
        self.db.commit()

    def bootstrap_owner(self, tenant_id: str, subject_id: str) -> None:
        """Offline bootstrap only. Production must restrict to trusted setup flow."""
        if not tenant_id or not subject_id:
            raise ValueError("Tenant and subject required")
        if self.db.execute("SELECT 1 FROM members WHERE tenant_id = ?", (tenant_id,)).fetchone():
            raise PermissionError("Tenant already initialized")
        self.db.execute(
            "INSERT INTO members(tenant_id,subject_id,role,active) VALUES (?,?,?,1)",
            (tenant_id, subject_id, Role.OWNER.value),
        )
        self.db.commit()

    def resolve(self, tenant_id: str, subject_id: str) -> Principal | None:
        if not tenant_id or not subject_id:
            return None
        row = self.db.execute(
            "SELECT role, active FROM members WHERE tenant_id=? AND subject_id=?",
            (tenant_id, subject_id),
        ).fetchone()
        if not row or not row[1]:
            return None
        try:
            role = Role(row[0])
        except ValueError:
            return None
        return Principal(subject_id, tenant_id, role)

    def set_member(self, actor: Principal, subject_id: str, role: Role, active: bool = True) -> None:
        """Revalidate actor from directory, never trust a client-provided role."""
        actual_actor = self.resolve(actor.tenant_id, actor.subject_id)
        require_permission(actual_actor, Action.MANAGE_TEAM, Resource(actor.tenant_id))
        if not subject_id:
            raise ValueError("Subject required")
        role = Role(role)
        existing = self.resolve(actor.tenant_id, subject_id)
        if subject_id == actor.subject_id:
            raise PermissionError("Cannot change your own membership")
        if existing is not None and existing.role == Role.OWNER:
            raise PermissionError("Cannot modify another owner using this operation")
        self.db.execute(
            """INSERT INTO members(tenant_id,subject_id,role,active) VALUES(?,?,?,?)
               ON CONFLICT(tenant_id,subject_id) DO UPDATE SET role=excluded.role,active=excluded.active""",
            (actor.tenant_id, subject_id, role.value, int(active)),
        )
        self.db.commit()

    def authorize(self, token_session: Principal | None, action: Action, tenant_id: str) -> bool:
        """Recheck membership and role freshness on every protected operation."""
        if token_session is None or token_session.tenant_id != tenant_id:
            return False
        from access_policy import authorized
        actual = self.resolve(tenant_id, token_session.subject_id)
        return authorized(actual, action, Resource(tenant_id))
