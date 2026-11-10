"""Tenant-scoped business invitations for existing verified BAM identities.

Invites are owner-created, one-use, expire in 7 days, and bind to an email.
Trusted delivery is out-of-band. Acceptance must occur in a trusted backend
after verified BAM identity proof; client-supplied subject IDs are forbidden.
"""
import hashlib
import secrets
import time
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
            created_by TEXT NOT NULL)""")
        db.commit()

    @staticmethod
    def _digest(token):
        return hashlib.sha256(token.encode('utf-8')).hexdigest()

    def invite(self,*,owner_session,tenant_id,email,role,now=None):
        timestamp=int(time.time()) if now is None else now
        session=self.sessions.resolve_current(owner_session,
            directory=self.directory,now=timestamp)
        if (session is None or session.principal.tenant_id!=tenant_id
                or session.principal.role!=Role.OWNER):
            raise PermissionError('Active business owner required')
        email=normalize_email(email)
        role=Role(role)
        if role not in _ALLOWED_ROLES:
            raise PermissionError('Owner role cannot be granted by invitation')
        token=secrets.token_urlsafe(32)
        with self.db:
            self.db.execute("""INSERT INTO bam_business_invitations
                (token_hash,tenant_id,email,role,expires_at,created_by)
                VALUES (?,?,?,?,?,?)""",(self._digest(token),tenant_id,email,
                                          role.value,timestamp+604800,
                                          session.principal.subject_id))
        self.deliver(email,tenant_id,token)
        return {'invitation_created':True,'expires_at':timestamp+604800,
                'publishing_enabled':False}

    def accept_trusted(self,*,verified_subject_id,token,now=None):
        """Caller MUST authenticate verified_subject_id independently."""
        timestamp=int(time.time()) if now is None else now
        if not isinstance(token,str) or not 20<=len(token)<=256:
            raise PermissionError('Invalid invitation')
        row=self.db.execute("""SELECT tenant_id,email,role FROM bam_business_invitations
            WHERE token_hash=? AND consumed_at IS NULL AND expires_at>?""",
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
                AND expires_at>?""",(timestamp,self._digest(token),timestamp))
            if updated.rowcount!=1:
                raise PermissionError('Invitation already used')
            self.db.execute("""INSERT INTO members(tenant_id,subject_id,role,active)
                VALUES (?,?,?,1)""",(row[0],verified_subject_id,row[2]))
        return {'tenant_id':row[0],'role':row[2],
                'membership_created':True,'publishing_enabled':False}
