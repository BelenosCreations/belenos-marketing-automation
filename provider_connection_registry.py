"""Offline read-only provider connection metadata registry.

Stores secret-manager references, never OAuth tokens or client secrets.
A trusted server layer must authenticate callers and resolve vault references.
"""
import re
import sqlite3

_ALLOWED_STATES={'pending','connected','refresh_required','revoked'}
# Internal capability only; not a claim that a social-provider permission
# is authorized or connected. Future OAuth scopes need their own verifier.
_READ_ONLY_SCOPES=frozenset(('read_insights',))
_REF=re.compile(r'^[A-Za-z0-9_./:-]{1,256}$')

class ProviderConnectionRegistry:
    def __init__(self, db):
        self.db=db
        db.execute("""CREATE TABLE IF NOT EXISTS provider_connections (
            tenant_id TEXT NOT NULL, platform TEXT NOT NULL,
            account_id TEXT NOT NULL, vault_reference TEXT NOT NULL,
            scope TEXT NOT NULL, state TEXT NOT NULL,
            expires_at INTEGER, updated_at INTEGER NOT NULL,
            PRIMARY KEY(tenant_id,platform,account_id)
        )""")
        db.commit()

    def register_trusted(self, *, tenant_id, platform, account_id,
                         vault_reference, scope, state, expires_at, now):
        for value in (tenant_id,platform,account_id,scope):
            if not isinstance(value,str) or not value.strip() or len(value)>128:
                raise ValueError('Invalid connection identity')
        if (not isinstance(vault_reference,str)
                or not _REF.fullmatch(vault_reference)
                or state not in _ALLOWED_STATES
                or type(now) is not int or now<0
                or (expires_at is not None and
                    (type(expires_at) is not int or expires_at<0))):
            raise ValueError('Invalid connection metadata')
        if scope not in _READ_ONLY_SCOPES:
            raise ValueError('Unapproved internal analytics capability')
        # An old writer must not revive revoked credentials or overwrite
        # newer state. Revocation is terminal until a separately verified
        # re-authorization workflow exists (not implemented in this Alpha).
        with self.db:
            cursor=self.db.execute("""INSERT INTO provider_connections
                (tenant_id,platform,account_id,vault_reference,scope,state,
                expires_at,updated_at) VALUES (?,?,?,?,?,?,?,?)
                ON CONFLICT(tenant_id,platform,account_id) DO UPDATE SET
                vault_reference=excluded.vault_reference,
                scope=excluded.scope,state=excluded.state,
                expires_at=excluded.expires_at,updated_at=excluded.updated_at
                WHERE provider_connections.updated_at<excluded.updated_at
                AND provider_connections.state!='revoked'""",
                (tenant_id,platform,account_id,vault_reference,scope,state,
                 expires_at,now))
            if cursor.rowcount!=1:
                raise ValueError('Stale or revoked provider connection')
        return {'state':state,'publishing_enabled':False}

    def status(self, *, tenant_id, platform, account_id, now):
        if type(now) is not int or now<0:
            raise ValueError('Invalid timestamp')
        row=self.db.execute("""SELECT scope,state,expires_at,updated_at
            FROM provider_connections WHERE tenant_id=? AND platform=?
            AND account_id=?""",(tenant_id,platform,account_id)).fetchone()
        if row is None:
            return {'status':'not_connected','publishing_enabled':False}
        scope,state,expiry,updated=row
        # Legacy, unapproved or future-dated metadata is never sufficient
        # for an active analytics connection even if state says connected.
        if scope not in _READ_ONLY_SCOPES or updated>now:
            effective='refresh_required'
        else:
            effective=('expired' if state=='connected' and expiry is not None
                       and expiry<=now else state)
        return {'status':effective,'scope':scope,'updated_at':updated,
                'expires_at':expiry,'publishing_enabled':False}
