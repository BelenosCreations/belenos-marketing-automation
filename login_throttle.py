"""Persistent offline login throttling foundation.

Caller MUST enforce per-IP and global limits at the production gateway too.
Identifiers are hashed to avoid storing raw emails in this table.
"""
import hashlib
import time

class LoginThrottle:
    def __init__(self,db,*,max_failures=5,window_seconds=900):
        if type(max_failures) is not int or max_failures<1:
            raise ValueError('Invalid failure limit')
        if type(window_seconds) is not int or window_seconds<1:
            raise ValueError('Invalid throttle window')
        self.db=db
        self.max_failures=max_failures
        self.window_seconds=window_seconds
        db.execute("""CREATE TABLE IF NOT EXISTS bam_login_throttle (
            identity_hash TEXT PRIMARY KEY,
            window_start INTEGER NOT NULL,
            failures INTEGER NOT NULL)""")
        db.commit()

    @staticmethod
    def _key(email):
        from identity_auth import normalize_email
        return hashlib.sha256(normalize_email(email).encode('utf-8')).hexdigest()

    def check(self,*,email,now=None):
        timestamp=int(time.time()) if now is None else now
        row=self.db.execute("""SELECT window_start,failures
            FROM bam_login_throttle WHERE identity_hash=?""",
            (self._key(email),)).fetchone()
        if row and timestamp<row[0]+self.window_seconds and row[1]>=self.max_failures:
            raise PermissionError('Authentication temporarily unavailable')

    def failure(self,*,email,now=None):
        timestamp=int(time.time()) if now is None else now
        key=self._key(email)
        with self.db:
            row=self.db.execute("""SELECT window_start,failures
                FROM bam_login_throttle WHERE identity_hash=?""",(key,)).fetchone()
            if row is None or timestamp>=row[0]+self.window_seconds:
                self.db.execute("""INSERT INTO bam_login_throttle
                    (identity_hash,window_start,failures) VALUES (?,?,1)
                    ON CONFLICT(identity_hash) DO UPDATE SET
                    window_start=excluded.window_start,failures=1""",
                    (key,timestamp))
            else:
                self.db.execute("""UPDATE bam_login_throttle SET failures=failures+1
                    WHERE identity_hash=?""",(key,))

    def success(self,*,email):
        with self.db:
            self.db.execute("""DELETE FROM bam_login_throttle
                WHERE identity_hash=?""",(self._key(email),))
