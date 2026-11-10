"""One-use email verification and password recovery primitives.

A trusted backend MUST deliver tokens out-of-band to the registered email.
Tokens are returned only to an injected delivery callback, never to API users.
This is an offline foundation, not a mail-sending or public HTTP service.
"""
import hashlib
import secrets
import time
from identity_auth import _hash_password,_password_bytes,_ITERATIONS,normalize_email

class EmailCredentialRecovery:
    def __init__(self,*,db,auth,deliver):
        if not callable(deliver):
            raise ValueError('Trusted delivery callback required')
        self.db=db
        self.auth=auth
        self.deliver=deliver
        db.execute("""CREATE TABLE IF NOT EXISTS bam_email_actions (
            token_hash TEXT PRIMARY KEY, subject_id TEXT NOT NULL,
            purpose TEXT NOT NULL CHECK(purpose IN ('verify','reset')),
            expires_at INTEGER NOT NULL, consumed_at INTEGER)""")
        db.commit()

    @staticmethod
    def _now(now):
        value=int(time.time()) if now is None else now
        if type(value) is not int or value<0:
            raise ValueError('Invalid timestamp')
        return value

    @staticmethod
    def _digest(token):
        return hashlib.sha256(token.encode('utf-8')).hexdigest()

    def request(self,*,email,purpose,now=None):
        timestamp=self._now(now)
        if purpose not in ('verify','reset'):
            raise ValueError('Invalid purpose')
        email=normalize_email(email)
        row=self.db.execute("""SELECT subject_id,active,email_verified
            FROM bam_identities WHERE email=?""",(email,)).fetchone()
        # Generic response regardless of whether account exists.
        if row is None or row[1]!=1 or (purpose=='reset' and row[2]!=1):
            return {'request_accepted':True}
        token=secrets.token_urlsafe(32)
        with self.db:
            self.db.execute("""UPDATE bam_email_actions SET consumed_at=?
                WHERE subject_id=? AND purpose=? AND consumed_at IS NULL""",
                (timestamp,row[0],purpose))
            self.db.execute("""INSERT INTO bam_email_actions
                (token_hash,subject_id,purpose,expires_at)
                VALUES (?,?,?,?)""",
                (self._digest(token),row[0],purpose,timestamp+900))
        # The trusted callback is responsible for secure, private delivery.
        self.deliver(email,purpose,token)
        return {'request_accepted':True}

    def _consume(self,*,token,purpose,now):
        if not isinstance(token,str) or not 20<=len(token)<=256:
            raise PermissionError('Invalid or expired token')
        with self.db:
            row=self.db.execute("""SELECT subject_id FROM bam_email_actions
                WHERE token_hash=? AND purpose=? AND consumed_at IS NULL
                AND expires_at>?""",(self._digest(token),purpose,now)).fetchone()
            if row is None:
                raise PermissionError('Invalid or expired token')
            updated=self.db.execute("""UPDATE bam_email_actions SET consumed_at=?
                WHERE token_hash=? AND purpose=? AND consumed_at IS NULL
                AND expires_at>?""",(now,self._digest(token),purpose,now))
            if updated.rowcount!=1:
                raise PermissionError('Token already consumed')
        return row[0]

    def confirm_email(self,*,token,now=None):
        timestamp=self._now(now)
        subject=self._consume(token=token,purpose='verify',now=timestamp)
        self.auth.set_email_verified_trusted(subject_id=subject,verified=True)
        return {'email_verified':True}

    def reset_password(self,*,token,new_password,now=None):
        timestamp=self._now(now)
        encoded=_password_bytes(new_password)
        subject=self._consume(token=token,purpose='reset',now=timestamp)
        salt=secrets.token_bytes(32)
        digest=_hash_password(encoded,salt)
        with self.db:
            cursor=self.db.execute("""UPDATE bam_password_credentials
                SET salt=?,digest=?,iterations=? WHERE subject_id=?""",
                (salt,digest,_ITERATIONS,subject))
            if cursor.rowcount!=1:
                raise PermissionError('Password credential not found')
        self.auth.sessions.revoke_identity(subject,now=timestamp)
        return {'password_reset':True,'sessions_revoked':True}
