"""Server-side verification registry for editorial screening.

Attestations are stored by a trusted verification worker, not the mobile
client. This module does not itself verify external social identities.
"""
import sqlite3

class EditorialAttestations:
    def __init__(self,db):
        self.db=db
        db.execute("""CREATE TABLE IF NOT EXISTS editorial_attestations (
            tenant_id TEXT NOT NULL,
            original_url TEXT NOT NULL,
            platform TEXT NOT NULL,
            account_id TEXT NOT NULL,
            identity_verified INTEGER NOT NULL CHECK(identity_verified IN (0,1)),
            competitor_status TEXT NOT NULL CHECK(competitor_status IN ('cleared','possible','unknown')),
            verified_at INTEGER NOT NULL,
            expires_at INTEGER NOT NULL,
            PRIMARY KEY (tenant_id,original_url)
        )""")
        db.commit()

    def record_trusted(self, *, tenant_id, original_url, platform, account_id,
                       identity_verified, competitor_status, verified_at, expires_at):
        """Only trusted verification workers may call this; never expose as API."""
        if not all(isinstance(v,str) and v.strip() for v in
                   (tenant_id,original_url,platform,account_id)):
            raise ValueError('Identity fields required')
        if type(identity_verified) is not bool:
            raise ValueError('Verification must be boolean')
        if competitor_status not in ('cleared','possible','unknown'):
            raise ValueError('Invalid competitor status')
        if type(verified_at) is not int or type(expires_at) is not int or expires_at<=verified_at:
            raise ValueError('Invalid attestation lifetime')
        with self.db:
            self.db.execute("""INSERT INTO editorial_attestations VALUES (?,?,?,?,?,?,?,?)
                ON CONFLICT(tenant_id,original_url) DO UPDATE SET
                platform=excluded.platform,account_id=excluded.account_id,
                identity_verified=excluded.identity_verified,
                competitor_status=excluded.competitor_status,
                verified_at=excluded.verified_at,expires_at=excluded.expires_at""",
                (tenant_id,original_url,platform,account_id,int(identity_verified),
                 competitor_status,verified_at,expires_at))

    def resolve(self, *, tenant_id, original_url, now):
        row=self.db.execute("""SELECT platform,account_id,identity_verified,
            competitor_status FROM editorial_attestations
            WHERE tenant_id=? AND original_url=? AND verified_at<=? AND expires_at>?""",
            (tenant_id,original_url,now,now)).fetchone()
        if row is None:
            return None
        return dict(platform=row[0],account_id=row[1],
                    identity_verified=bool(row[2]),local_competitor_risk=row[3])
