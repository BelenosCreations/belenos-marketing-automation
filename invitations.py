"""Offline employee invitation lifecycle.

Invite links are secrets. This module does not send invitations or authenticate
recipients; redemption requires a verified subject supplied by trusted server.
"""
import hashlib
import secrets
import sqlite3
import time
from access_policy import Action, Role

class InvitationService:
    def __init__(self, db, directory, sessions):
        self.db=db
        self.directory=directory
        self.sessions=sessions
        db.execute("""CREATE TABLE IF NOT EXISTS invitations (
            token_hash TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            role TEXT NOT NULL,
            created_by TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            consumed_at INTEGER,
            revoked_at INTEGER
        )""")
        db.commit()

    def create(self, *, actor_token, tenant_id, role, now=None, ttl_seconds=86400):
        now=int(time.time()) if now is None else now
        if not isinstance(ttl_seconds,int) or isinstance(ttl_seconds,bool) or not 60<=ttl_seconds<=604800:
            raise ValueError('Invalid invitation TTL')
        session=self.sessions.resolve(actor_token,now=now)
        if session is None or not self.directory.authorize(session.principal,Action.MANAGE_TEAM,tenant_id):
            raise PermissionError('Owner authorization required')
        role=Role(role)
        if role==Role.OWNER:
            raise PermissionError('Owner invitations require separate privileged process')
        token=secrets.token_urlsafe(32)
        self.db.execute('INSERT INTO invitations VALUES (?,?,?,?,?,NULL,NULL)',
                        (hashlib.sha256(token.encode()).hexdigest(),tenant_id,role.value,session.principal.subject_id,now+ttl_seconds))
        self.db.commit()
        return token

    def redeem(self, *, token, tenant_id, verified_subject_id, now=None):
        """Caller MUST authenticate verified_subject_id before calling."""
        now=int(time.time()) if now is None else now
        if not isinstance(token,str) or not token or not verified_subject_id or not tenant_id:
            raise PermissionError('Invalid invitation')
        digest=hashlib.sha256(token.encode()).hexdigest()
        row=self.db.execute("""SELECT role FROM invitations
            WHERE token_hash=? AND tenant_id=? AND expires_at>? AND consumed_at IS NULL AND revoked_at IS NULL""",
            (digest,tenant_id,now)).fetchone()
        if row is None:
            raise PermissionError('Invitation expired, revoked, or already used')
        if self.directory.resolve(tenant_id,verified_subject_id) is not None:
            raise PermissionError('Existing member cannot redeem invitation')
        # Directory provisioning and token consumption are committed together
        # by a savepoint so failed redemption cannot consume the invitation.
        self.db.execute('SAVEPOINT redeem_invite')
        try:
            self.db.execute('INSERT INTO members(tenant_id,subject_id,role,active) VALUES (?,?,?,1)',
                            (tenant_id,verified_subject_id,row[0]))
            changed=self.db.execute("""UPDATE invitations SET consumed_at=?
                WHERE token_hash=? AND tenant_id=? AND consumed_at IS NULL AND revoked_at IS NULL AND expires_at>?""",
                (now,digest,tenant_id,now)).rowcount
            if changed!=1:
                raise PermissionError('Invitation no longer valid')
            self.db.execute('RELEASE SAVEPOINT redeem_invite')
            self.db.commit()
        except Exception:
            self.db.execute('ROLLBACK TO SAVEPOINT redeem_invite')
            self.db.execute('RELEASE SAVEPOINT redeem_invite')
            raise

    def revoke(self, *, actor_token, tenant_id, invite_token, now=None):
        now=int(time.time()) if now is None else now
        session=self.sessions.resolve(actor_token,now=now)
        if session is None or not self.directory.authorize(session.principal,Action.MANAGE_TEAM,tenant_id):
            raise PermissionError('Owner authorization required')
        self.db.execute("""UPDATE invitations SET revoked_at=?
            WHERE token_hash=? AND tenant_id=? AND consumed_at IS NULL AND revoked_at IS NULL""",
            (now,hashlib.sha256(invite_token.encode()).hexdigest(),tenant_id))
        self.db.commit()
