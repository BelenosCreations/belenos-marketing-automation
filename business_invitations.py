"""Tenant-scoped business invitations for existing verified BAM identities.

Invites are owner-created, one-use, expire in 7 days, and bind to an email.
Trusted delivery is out-of-band. Acceptance must occur in a trusted backend
after verified BAM identity proof; client-supplied subject IDs are forbidden.
"""
import hashlib
import secrets
import time
import uuid
from access_policy import Role
from identity_auth import normalize_email

_ALLOWED_ROLES={Role.MARKETING_MANAGER,Role.CONTENT_CREATOR,Role.EMPLOYEE,Role.VIEWER}

class BusinessInvitations:
    def __init__(self,*,db,sessions,directory,auth,deliver):
        if not callable(deliver):
            raise ValueError('Trusted invitation delivery callback required')
        self.db=db
        self.sessions=sessions
        self.directory=directory
        self.auth=auth
        self.deliver=deliver
        db.execute("""CREATE TABLE IF NOT EXISTS bam_business_invitations (
            token_hash TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
            email TEXT NOT NULL, role TEXT NOT NULL,
            expires_at INTEGER NOT NULL, consumed_at INTEGER,
            created_by TEXT NOT NULL,
            invitation_id TEXT,
            revoked_at INTEGER,
            delivery_state TEXT NOT NULL DEFAULT 'delivered')""")
        columns={row[1] for row in db.execute(
            'PRAGMA table_info(bam_business_invitations)')}
        if 'invitation_id' not in columns:
            db.execute("""ALTER TABLE bam_business_invitations
                ADD COLUMN invitation_id TEXT""")
        if 'revoked_at' not in columns:
            db.execute("""ALTER TABLE bam_business_invitations
                ADD COLUMN revoked_at INTEGER""")
        if 'delivery_state' not in columns:
            # Old rows may already have been handed to a trusted delivery
            # callback; preserve their validity on schema migration.
            db.execute("""ALTER TABLE bam_business_invitations
                ADD COLUMN delivery_state TEXT NOT NULL DEFAULT 'delivered'""")
        for (digest,) in db.execute("""SELECT token_hash FROM
                 bam_business_invitations WHERE invitation_id IS NULL""").fetchall():
            db.execute("""UPDATE bam_business_invitations
                SET invitation_id=? WHERE token_hash=?
                AND invitation_id IS NULL""",
                (uuid.uuid4().hex,digest))
        db.execute("""CREATE UNIQUE INDEX IF NOT EXISTS
            bam_business_invitation_public_id
            ON bam_business_invitations(invitation_id)""")
        # New append-only trusted server metadata. Prior historical actions
        # cannot be reconstructed; do not backfill invented audit entries.
        db.execute("""CREATE TABLE IF NOT EXISTS bam_business_invitation_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            invitation_id TEXT NOT NULL,
            action TEXT NOT NULL CHECK(action IN
                ('delivered','delivery_failed','cancelled','accepted')),
            actor_id TEXT NOT NULL,
            occurred_at INTEGER NOT NULL
        )""")
        db.commit()

    @staticmethod
    def _digest(token):
        return hashlib.sha256(token.encode('utf-8')).hexdigest()

    def _owner(self,session_token,now):
        if type(now) is not int or now<0:
            raise ValueError('Trusted timestamp required')
        session=self.sessions.resolve_current(
            session_token,directory=self.directory,now=now)
        if session is None or session.principal.role!=Role.OWNER:
            raise PermissionError('Current business owner session required')
        return session.principal

    def pending_current(self,*,owner_session,now=None):
        """Bounded owner-only pending invitation preview; no bearer secrets."""
        timestamp=int(time.time()) if now is None else now
        principal=self._owner(owner_session,timestamp)
        rows=self.db.execute("""SELECT invitation_id,email,role,expires_at
            FROM bam_business_invitations
            WHERE tenant_id=? AND revoked_at IS NULL
                AND consumed_at IS NULL AND expires_at>?
                AND delivery_state='delivered'
            ORDER BY expires_at,invitation_id LIMIT 50""",
            (principal.tenant_id,timestamp)).fetchall()
        if any(r[0] is None for r in rows):
            raise RuntimeError('Invalid invitation migration')
        return {'tenant_id':principal.tenant_id,
                'status':'private_pending_invitations',
                'items':[{'invitation_id':r[0],'email':r[1],
                          'role':r[2],'expires_at':r[3]} for r in rows],
                'publishing_enabled':False}

    def history_current(self,*,owner_session,now=None,limit=30):
        """Owner-only append-only event preview without token/email data.

        Events before installation are not fabricated or backfilled. No
        invitation bearer secret, digest, or recipient address is returned.
        """
        timestamp=int(time.time()) if now is None else now
        principal=self._owner(owner_session,timestamp)
        if type(limit) is not int or not 1<=limit<=30:
            raise ValueError('Bounded invitation activity requested')
        rows=self.db.execute("""SELECT invitation_id,action,occurred_at
            FROM bam_business_invitation_events
            WHERE tenant_id=? ORDER BY event_id DESC LIMIT ?""",
            (principal.tenant_id,limit)).fetchall()
        return {'tenant_id':principal.tenant_id,
                'status':'private_invitation_activity',
                'events':[{'invitation_id':row[0],
                           'action':row[1],'occurred_at':row[2]}
                          for row in rows],
                'publishing_enabled':False}

    def cancel_current(self,*,owner_session,invitation_id,now=None):
        """Cancel a one-business unconsumed invitation without token exposure."""
        timestamp=int(time.time()) if now is None else now
        principal=self._owner(owner_session,timestamp)
        if (type(invitation_id) is not str or len(invitation_id)!=32 or
                any(c not in '0123456789abcdef' for c in invitation_id)):
            raise ValueError('Valid invitation identifier required')
        with self.db:
            updated=self.db.execute("""UPDATE bam_business_invitations
                SET revoked_at=? WHERE invitation_id=? AND tenant_id=?
                AND revoked_at IS NULL AND consumed_at IS NULL
                AND expires_at>? AND delivery_state='delivered'""",
                (timestamp,invitation_id,principal.tenant_id,timestamp))
            if updated.rowcount!=1:
                raise KeyError('Active invitation not found')
            self.db.execute("""INSERT INTO bam_business_invitation_events
                (tenant_id,invitation_id,action,actor_id,occurred_at)
                VALUES (?,?,'cancelled',?,?)""",
                (principal.tenant_id,invitation_id,
                 principal.subject_id,timestamp))
        return {'tenant_id':principal.tenant_id,
                'invitation_id':invitation_id,
                'status':'cancelled','publishing_enabled':False}

    def invite(self,*,owner_session,tenant_id,email,role,now=None):
        timestamp=int(time.time()) if now is None else now
        principal=self._owner(owner_session,timestamp)
        if principal.tenant_id!=tenant_id:
            raise PermissionError('Active business owner required')
        email=normalize_email(email)
        role=Role(role)
        if role not in _ALLOWED_ROLES:
            raise PermissionError('Owner role cannot be granted by invitation')
        token=secrets.token_urlsafe(32)
        invitation_id=uuid.uuid4().hex
        digest=self._digest(token)
        # A single atomic INSERT ... SELECT prevents duplicate active
        # invitations from being created by simultaneous owner requests.
        # Expired, consumed and explicitly cancelled links do not block a
        # fresh invite. An existing membership (even deactivated) must be
        # handled through team administration, never another invite link.
        with self.db:
            created=self.db.execute("""INSERT INTO bam_business_invitations
                (token_hash,tenant_id,email,role,expires_at,created_by,
                 invitation_id,delivery_state)
                SELECT ?,?,?,?,?,?,?,'pending'
                WHERE NOT EXISTS (
                    SELECT 1 FROM bam_business_invitations
                    WHERE tenant_id=? AND email=? AND consumed_at IS NULL
                    AND revoked_at IS NULL AND expires_at>?
                    AND delivery_state IN ('pending','delivered'))
                AND NOT EXISTS (
                    SELECT 1 FROM members m JOIN bam_identities i
                    ON i.subject_id=m.subject_id
                    WHERE m.tenant_id=? AND i.email=?)""",
                (digest,tenant_id,email,role.value,timestamp+604800,
                 principal.subject_id,invitation_id,
                 tenant_id,email,timestamp,tenant_id,email))
            if created.rowcount!=1:
                raise ValueError('Active invitation or existing membership for business')
        # The token is never returned from this service. An invitation is not
        # redeemable until trusted delivery returns successfully.
        try:
            self.deliver(email,tenant_id,token)
        except Exception as exc:
            with self.db:
                changed=self.db.execute("""UPDATE bam_business_invitations
                    SET delivery_state='failed',revoked_at=?
                    WHERE token_hash=? AND delivery_state='pending'""",
                    (timestamp,digest))
                if changed.rowcount==1:
                    self.db.execute("""INSERT INTO bam_business_invitation_events
                        (tenant_id,invitation_id,action,actor_id,occurred_at)
                        VALUES (?,?,'delivery_failed',?,?)""",
                        (tenant_id,invitation_id,principal.subject_id,timestamp))
            raise RuntimeError('Trusted invitation delivery unavailable') from exc
        with self.db:
            changed=self.db.execute("""UPDATE bam_business_invitations
                SET delivery_state='delivered'
                WHERE token_hash=? AND delivery_state='pending'
                AND revoked_at IS NULL""",(digest,))
            if changed.rowcount!=1:
                raise RuntimeError('Invitation could not be finalized')
            self.db.execute("""INSERT INTO bam_business_invitation_events
                (tenant_id,invitation_id,action,actor_id,occurred_at)
                VALUES (?,?,'delivered',?,?)""",
                (tenant_id,invitation_id,principal.subject_id,timestamp))
        return {'invitation_created':True,'expires_at':timestamp+604800,
                'invitation_id':invitation_id,'publishing_enabled':False}

    def accept_trusted(self,*,verified_subject_id,token,now=None):
        """Caller MUST authenticate verified_subject_id independently."""
        timestamp=int(time.time()) if now is None else now
        if not isinstance(token,str) or not 20<=len(token)<=256:
            raise PermissionError('Invalid invitation')
        row=self.db.execute("""SELECT tenant_id,email,role FROM bam_business_invitations
            WHERE token_hash=? AND consumed_at IS NULL AND expires_at>?
            AND revoked_at IS NULL AND delivery_state='delivered'""",
            (self._digest(token),timestamp)).fetchone()
        if row is None:
            raise PermissionError('Invitation expired or used')
        identity=self.db.execute("""SELECT email,active,email_verified
            FROM bam_identities WHERE subject_id=?""",
            (verified_subject_id,)).fetchone()
        if identity is None or identity!=(row[1],1,1):
            raise PermissionError('Invitation does not match verified BAM identity')
        # Owner membership must still exist and be active at acceptance time.
        creator=self.db.execute("""SELECT created_by FROM bam_business_invitations
            WHERE token_hash=?""",(self._digest(token),)).fetchone()
        if creator is None or self.directory.resolve(row[0],creator[0]) is None:
            raise PermissionError('Inviting owner no longer active')
        owner=self.directory.resolve(row[0],creator[0])
        if owner.role!=Role.OWNER:
            raise PermissionError('Inviting owner no longer authorized')
        if self.directory.resolve(row[0],verified_subject_id) is not None:
            raise PermissionError('Already a business member')
        with self.db:
            updated=self.db.execute("""UPDATE bam_business_invitations
                SET consumed_at=? WHERE token_hash=? AND consumed_at IS NULL
                AND expires_at>? AND revoked_at IS NULL
                AND delivery_state='delivered'""",
                (timestamp,self._digest(token),timestamp))
            if updated.rowcount!=1:
                raise PermissionError('Invitation already used')
            self.db.execute("""INSERT INTO members(tenant_id,subject_id,role,active)
                VALUES (?,?,?,1)""",(row[0],verified_subject_id,row[2]))
            identifier=self.db.execute("""SELECT invitation_id
                FROM bam_business_invitations WHERE token_hash=?""",
                (self._digest(token),)).fetchone()
            if identifier is None or identifier[0] is None:
                raise RuntimeError('Invitation identifier missing')
            self.db.execute("""INSERT INTO bam_business_invitation_events
                (tenant_id,invitation_id,action,actor_id,occurred_at)
                VALUES (?,?,'accepted',?,?)""",
                (row[0],identifier[0],verified_subject_id,timestamp))
        return {'tenant_id':row[0],'role':row[2],
                'membership_created':True,'publishing_enabled':False}
