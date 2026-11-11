"""One-time Google sign-in nonce ledger for a trusted BAM backend.

The client receives a random challenge ID and nonce. A Google ID token must
include that nonce. Consumption is atomic and one-time, even on failed login.
"""
import hashlib
import secrets
import time

class GoogleLoginChallenges:
    def __init__(self,db):
        self.db=db
        db.execute("""CREATE TABLE IF NOT EXISTS bam_google_challenges (
            challenge_hash TEXT PRIMARY KEY,
            nonce TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            consumed_at INTEGER)""")
        db.commit()

    @staticmethod
    def _hash(value):
        return hashlib.sha256(value.encode('utf-8')).hexdigest()

    def begin(self,*,now=None):
        timestamp=int(time.time()) if now is None else now
        if type(timestamp) is not int or timestamp<0:
            raise ValueError('Invalid time')
        challenge=secrets.token_urlsafe(32)
        nonce=secrets.token_urlsafe(32)
        with self.db:
            self.db.execute("""INSERT INTO bam_google_challenges
                (challenge_hash,nonce,expires_at) VALUES (?,?,?)""",
                (self._hash(challenge),nonce,timestamp+300))
        return {'challenge_id':challenge,'nonce':nonce,'expires_at':timestamp+300}

    def consume(self,*,challenge_id,now=None):
        timestamp=int(time.time()) if now is None else now
        if not isinstance(challenge_id,str) or not 20<=len(challenge_id)<=256:
            raise PermissionError('Invalid Google challenge')
        with self.db:
            row=self.db.execute("""SELECT nonce FROM bam_google_challenges
                WHERE challenge_hash=? AND consumed_at IS NULL AND expires_at>?""",
                (self._hash(challenge_id),timestamp)).fetchone()
            if row is None:
                raise PermissionError('Expired or consumed Google challenge')
            cursor=self.db.execute("""UPDATE bam_google_challenges SET consumed_at=?
                WHERE challenge_hash=? AND consumed_at IS NULL AND expires_at>?""",
                (timestamp,self._hash(challenge_id),timestamp))
            if cursor.rowcount!=1:
                raise PermissionError('Google challenge already consumed')
        return row[0]
