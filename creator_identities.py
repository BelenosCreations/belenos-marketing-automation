"""Offline per-business creator identity screening.

Identity is a verified (platform, account_id) pair, never a display name or
shared platform domain. Verification is external and must be trusted-server-side.
No automatic publishing or network calls are provided.
"""
import sqlite3

class CreatorIdentityPolicy:
    def __init__(self, db: sqlite3.Connection):
        self.db = db
        db.execute("""CREATE TABLE IF NOT EXISTS creator_identities (
            tenant_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            account_id TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('approved','blocked','review')),
            reason TEXT NOT NULL,
            PRIMARY KEY (tenant_id,platform,account_id)
        )""")
        db.commit()

    @staticmethod
    def _validate(tenant_id, platform, account_id):
        for value in (tenant_id,platform,account_id):
            if not isinstance(value,str) or not value.strip():
                raise ValueError('Tenant, platform and verified account ID required')
        if platform not in ('facebook','instagram','youtube','tiktok','other'):
            raise ValueError('Unsupported platform')

    def set_status(self, *, tenant_id, platform, account_id, status, reason):
        """Trusted administrator operation, not an unprotected HTTP endpoint."""
        self._validate(tenant_id,platform,account_id)
        if status not in ('approved','blocked','review'):
            raise ValueError('Invalid creator status')
        if not isinstance(reason,str) or not reason.strip():
            raise ValueError('Reason required')
        with self.db:
            self.db.execute("""INSERT INTO creator_identities VALUES (?,?,?,?,?)
                ON CONFLICT(tenant_id,platform,account_id) DO UPDATE SET
                status=excluded.status,reason=excluded.reason""",
                (tenant_id,platform,account_id,status,reason))

    def screen(self, *, tenant_id, platform, account_id, identity_verified):
        """Never trust caller assertions of verification in a public API."""
        try:
            self._validate(tenant_id,platform,account_id)
        except ValueError:
            return 'blocked','invalid_creator_identity'
        if identity_verified is not True:
            return 'approval_required','identity_not_verified'
        row=self.db.execute("""SELECT status FROM creator_identities
            WHERE tenant_id=? AND platform=? AND account_id=?""",
            (tenant_id,platform,account_id)).fetchone()
        if row is None or row[0]=='review':
            return 'approval_required','creator_review_required'
        if row[0]=='blocked':
            return 'blocked','business_specific_competitor_or_exclusion'
        return 'eligible','creator_approved_for_business'
