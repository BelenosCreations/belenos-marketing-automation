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
    def _time(now):
        timestamp=int(time.time()) if now is None else now
        if type(timestamp) is not int or timestamp<0 or timestamp>253402300799:
            raise ValueError('Invalid trusted throttle time')
        return timestamp

    @staticmethod
    def _key(email):
        from identity_auth import normalize_email
        return hashlib.sha256(normalize_email(email).encode('utf-8')).hexdigest()

    def check(self,*,email,now=None):
        timestamp=self._time(now)
        row=self.db.execute("""SELECT window_start,failures
            FROM bam_login_throttle WHERE identity_hash=?""",
            (self._key(email),)).fetchone()
        if row and timestamp<row[0]+self.window_seconds and row[1]>=self.max_failures:
            raise PermissionError('Authentication temporarily unavailable')

    def failure(self,*,email,now=None):
        timestamp=self._time(now)
        key=self._key(email)
        # One SQL statement avoids lost counts across independent DB clients.
        # A backdated request cannot rewind a more recent lockout window.
        # check() + authentication + failure() is NOT an atomic admission
        # operation; production still requires IP/global abuse controls.
        with self.db:
            self.db.execute("""INSERT INTO bam_login_throttle
                (identity_hash,window_start,failures) VALUES (?,?,1)
                ON CONFLICT(identity_hash) DO UPDATE SET
                failures=CASE
                  WHEN excluded.window_start>=
                    bam_login_throttle.window_start+?
                  THEN 1 ELSE bam_login_throttle.failures+1 END,
                window_start=CASE
                  WHEN excluded.window_start>=
                    bam_login_throttle.window_start+?
                  THEN excluded.window_start
                  ELSE bam_login_throttle.window_start END""",
                (key,timestamp,self.window_seconds,self.window_seconds))

    def success(self,*,email):
        with self.db:
            self.db.execute("""DELETE FROM bam_login_throttle
                WHERE identity_hash=?""",(self._key(email),))
