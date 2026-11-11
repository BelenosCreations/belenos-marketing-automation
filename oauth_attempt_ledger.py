"""Offline OAuth authorization attempt ledger with PKCE and one-time state.

Does not build authorization URLs, exchange codes, or store provider tokens.
Only a trusted backend should invoke these methods.
"""
import hashlib
import hmac
import secrets
import sqlite3
import time
import base64

def _digest(value):
    return hashlib.sha256(value.encode('ascii')).hexdigest()

class OAuthAttemptLedger:
    def __init__(self, db):
        self.db=db
        db.execute("""CREATE TABLE IF NOT EXISTS oauth_attempts (
            state_hash TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
            platform TEXT NOT NULL, account_id TEXT NOT NULL,
            verifier_hash TEXT NOT NULL, expires_at INTEGER NOT NULL,
            consumed_at INTEGER
        )""")
        db.commit()

    def begin_trusted(self, *, tenant_id, platform, account_id, now=None,
                      ttl_seconds=600):
        now=int(time.time()) if now is None else now
        if (any(not isinstance(x,str) or not x.strip() or len(x)>128
                for x in (tenant_id,platform,account_id))
                or type(now) is not int or now<0
                or type(ttl_seconds) is not int or not 60<=ttl_seconds<=900):
            raise ValueError('Invalid OAuth attempt')
        state=secrets.token_urlsafe(32)
        verifier=secrets.token_urlsafe(48)
        challenge=base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode('ascii')).digest()
        ).decode('ascii').rstrip('=')
        with self.db:
            self.db.execute("""INSERT INTO oauth_attempts
                (state_hash,tenant_id,platform,account_id,verifier_hash,
                 expires_at,consumed_at) VALUES (?,?,?,?,?,?,NULL)""",
                (_digest(state),tenant_id,platform,account_id,
                 _digest(verifier),now+ttl_seconds))
        return {'state':state,'code_verifier':verifier,
                'code_challenge':challenge,'code_challenge_method':'S256',
                'expires_at':now+ttl_seconds,'publishing_enabled':False}

    def consume_trusted(self, *, tenant_id, platform, account_id,
                        state, code_verifier, now=None):
        now=int(time.time()) if now is None else now
        if (type(now) is not int or now<0
                or not isinstance(state,str) or not 16<=len(state)<=256
                or not isinstance(code_verifier,str)
                or not 43<=len(code_verifier)<=128
                or not state.isascii() or not code_verifier.isascii()):
            raise ValueError('Invalid OAuth callback')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            row=self.db.execute("""SELECT tenant_id,platform,account_id,
                verifier_hash,expires_at,consumed_at FROM oauth_attempts
                WHERE state_hash=?""",(_digest(state),)).fetchone()
            if (row is None or row[5] is not None or row[4]<=now
                    or row[:3]!=(tenant_id,platform,account_id)
                    or not hmac.compare_digest(row[3],_digest(code_verifier))):
                raise PermissionError('OAuth state invalid, expired or consumed')
            cursor=self.db.execute("""UPDATE oauth_attempts SET consumed_at=?
                WHERE state_hash=? AND consumed_at IS NULL AND expires_at>?""",
                (now,_digest(state),now))
            if cursor.rowcount!=1:
                raise PermissionError('OAuth attempt already consumed')
        return {'state_verified':True,'account_id':account_id,
                'token_exchange_performed':False,'publishing_enabled':False}
