"""BAM identity authentication foundation (offline, no provider networking).

Password credentials are PBKDF2-HMAC-SHA256 hashes with random salts. Google
sign-in ONLY accepts a verified identity from a trusted server-side verifier;
never pass raw client Google claims into login_google_verified.

Registration does not grant business membership or create an active session.
Production must add verified-email enrollment, rate limiting, MFA/recovery,
HTTPS, persistent storage, and real Google ID-token verification.
"""
import hashlib
import hmac
import secrets
import sqlite3
import time
import uuid

from access_policy import Role

_ITERATIONS=600_000
_MAX_EMAIL=254
_MAX_PASSWORD_BYTES=1024

def normalize_email(email):
    if not isinstance(email,str):
        raise ValueError('Invalid email')
    email=email.strip().lower()
    if (not email or len(email)>_MAX_EMAIL or email.count('@')!=1
            or any(c.isspace() or ord(c)<33 for c in email)):
        raise ValueError('Invalid email')
    local,domain=email.split('@')
    if not local or not domain or '.' not in domain or domain.startswith('.') or domain.endswith('.'):
        raise ValueError('Invalid email')
    return email

def _password_bytes(password):
    if not isinstance(password,str):
        raise ValueError('Invalid password')
    encoded=password.encode('utf-8')
    if len(encoded)<12 or len(encoded)>_MAX_PASSWORD_BYTES:
        raise ValueError('Password must be between 12 and 1024 UTF-8 bytes')
    return encoded

def _hash_password(password,salt):
    return hashlib.pbkdf2_hmac('sha256',password,salt,_ITERATIONS)

class IdentityAuth:
    def __init__(self,db,sessions,directory):
        self.db=db
        self.sessions=sessions
        self.directory=directory
        db.execute("""CREATE TABLE IF NOT EXISTS bam_identities (
            subject_id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE,
            email_verified INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1,
            created_at INTEGER NOT NULL)""")
        db.execute("""CREATE TABLE IF NOT EXISTS bam_password_credentials (
            subject_id TEXT PRIMARY KEY REFERENCES bam_identities(subject_id),
            salt BLOB NOT NULL, digest BLOB NOT NULL, iterations INTEGER NOT NULL)""")
        db.execute("""CREATE TABLE IF NOT EXISTS bam_google_identities (
            google_sub TEXT PRIMARY KEY,
            subject_id TEXT NOT NULL UNIQUE REFERENCES bam_identities(subject_id))""")
        db.commit()

    def register_password(self,*,email,password,now=None):
        """Trusted enrollment only: does not verify email or grant memberships."""
        email=normalize_email(email)
        encoded=_password_bytes(password)
        timestamp=int(time.time()) if now is None else now
        if type(timestamp) is not int or timestamp<0:
            raise ValueError('Invalid timestamp')
        subject=uuid.uuid4().hex
        salt=secrets.token_bytes(32)
        digest=_hash_password(encoded,salt)
        with self.db:
            self.db.execute("""INSERT INTO bam_identities
                (subject_id,email,email_verified,active,created_at)
                VALUES (?,?,0,1,?)""",(subject,email,timestamp))
            self.db.execute("""INSERT INTO bam_password_credentials
                (subject_id,salt,digest,iterations) VALUES (?,?,?,?)""",
                (subject,salt,digest,_ITERATIONS))
        return subject

    def set_email_verified_trusted(self,*,subject_id,verified):
        """Only trusted verification callbacks may invoke this method."""
        if type(verified) is not bool:
            raise ValueError('Boolean verification required')
        with self.db:
            cursor=self.db.execute("""UPDATE bam_identities SET email_verified=?
                WHERE subject_id=?""",(int(verified),subject_id))
        if cursor.rowcount!=1:
            raise KeyError('Unknown identity')

    def _issue_for_member(self,subject_id,tenant_id,now):
        if not isinstance(tenant_id,str) or not tenant_id:
            raise PermissionError('Business membership required')
        member=self.directory.resolve(tenant_id,subject_id)
        if member is None:
            raise PermissionError('Business membership required')
        return self.sessions.issue(member,now=now)

    def login_password(self,*,email,password,tenant_id,now=None):
        """Require verified email and active tenant membership before session."""
        timestamp=int(time.time()) if now is None else now
        email=normalize_email(email)
        encoded=_password_bytes(password)
        row=self.db.execute("""SELECT i.subject_id,i.active,i.email_verified,
                p.salt,p.digest,p.iterations
                FROM bam_identities i LEFT JOIN bam_password_credentials p
                ON p.subject_id=i.subject_id WHERE i.email=?""",(email,)).fetchone()
        # A constant dummy KDF avoids obvious timing differences for missing email.
        salt=row[3] if row and row[3] is not None else b'\0'*32
        actual=_hash_password(encoded,salt)
        expected=row[4] if row and row[4] is not None else b'\0'*32
        if (not hmac.compare_digest(actual,expected) or row is None
                or row[1]!=1 or row[2]!=1 or row[5]!=_ITERATIONS):
            raise PermissionError('Invalid credentials or account not verified')
        return self._issue_for_member(row[0],tenant_id,timestamp)

    def link_google_verified(self,*,subject_id,google_sub,email,email_verified):
        """Trusted, explicit account linking after independent identity proof.

        A matching email by itself never links a Google account.
        """
        if (not isinstance(google_sub,str) or not google_sub.strip()
                or len(google_sub)>255 or type(email_verified) is not bool
                or not email_verified):
            raise PermissionError('Verified Google subject required')
        email=normalize_email(email)
        row=self.db.execute("""SELECT email,active,email_verified FROM bam_identities
            WHERE subject_id=?""",(subject_id,)).fetchone()
        if row is None or row!=(email,1,1):
            raise PermissionError('Verified existing BAM identity required')
        with self.db:
            self.db.execute("""INSERT INTO bam_google_identities
                (google_sub,subject_id) VALUES (?,?)""",(google_sub,subject_id))

    def login_google_verified(self,*,google_sub,email,email_verified,tenant_id,now=None):
        """Accept ONLY claims already verified by trusted Google token verifier.

        The caller must check Google signature, issuer, audience, expiration,
        nonce when used, and email_verified before calling this method.
        """
        if (not isinstance(google_sub,str) or not google_sub.strip()
                or len(google_sub)>255 or email_verified is not True):
            raise PermissionError('Google identity not verified')
        email=normalize_email(email)
        timestamp=int(time.time()) if now is None else now
        row=self.db.execute("""SELECT i.subject_id,i.email,i.active,i.email_verified
            FROM bam_google_identities g JOIN bam_identities i
            ON g.subject_id=i.subject_id WHERE g.google_sub=?""",
            (google_sub,)).fetchone()
        if row is None or row[1]!=email or row[2]!=1 or row[3]!=1:
            raise PermissionError('Google identity not linked or inactive')
        return self._issue_for_member(row[0],tenant_id,timestamp)

    def change_password(self,*,session_token,current_password,new_password,now=None):
        """Authenticated password change; revokes all existing BAM sessions."""
        timestamp=int(time.time()) if now is None else now
        session=self.sessions.resolve_current(session_token,
            directory=self.directory,now=timestamp)
        if session is None:
            raise PermissionError('Active BAM session required')
        subject=session.principal.subject_id
        row=self.db.execute("""SELECT i.email,p.salt,p.digest,p.iterations
            FROM bam_identities i JOIN bam_password_credentials p
            ON i.subject_id=p.subject_id
            WHERE i.subject_id=? AND i.active=1 AND i.email_verified=1""",
            (subject,)).fetchone()
        if row is None or row[3]!=_ITERATIONS:
            raise PermissionError('Verified password account required')
        current=_password_bytes(current_password)
        if not hmac.compare_digest(_hash_password(current,row[1]),row[2]):
            raise PermissionError('Current password invalid')
        updated=_password_bytes(new_password)
        if hmac.compare_digest(current,updated):
            raise ValueError('New password must be different')
        salt=secrets.token_bytes(32)
        digest=_hash_password(updated,salt)
        with self.db:
            self.db.execute("""UPDATE bam_password_credentials
                SET salt=?,digest=?,iterations=? WHERE subject_id=?""",
                (salt,digest,_ITERATIONS,subject))
        self.sessions.revoke_identity(subject,now=timestamp)
        return {'password_changed':True,'sessions_revoked':True}

    def disable_identity_trusted(self,*,subject_id,now=None):
        """Administrative action, not exposed to untrusted clients."""
        timestamp=int(time.time()) if now is None else now
        with self.db:
            cursor=self.db.execute("""UPDATE bam_identities SET active=0
                WHERE subject_id=?""",(subject_id,))
        if cursor.rowcount!=1:
            raise KeyError('Unknown identity')
        self.sessions.revoke_identity(subject_id,now=timestamp)
