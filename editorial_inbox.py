"""Tenant-isolated editorial inbox for vetted external links.

The queue is review-only. No scheduling, posting, or media downloads.
"""
import sqlite3
from urllib.parse import urlparse

class EditorialInbox:
    def __init__(self, db, recommendation_gate):
        self.db=db
        self.gate=recommendation_gate
        db.execute("""CREATE TABLE IF NOT EXISTS editorial_inbox (
            tenant_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            account_id TEXT NOT NULL,
            original_url TEXT NOT NULL,
            topic TEXT NOT NULL,
            summary TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('review','blocked')),
            reason TEXT NOT NULL,
            PRIMARY KEY(tenant_id, original_url)
        )""")
        db.commit()

    def consider(self, *, tenant_id, topic, candidate, platform, account_id,
                 identity_verified=False, local_competitor_risk='unknown'):
        """Only trusted discovery may supply identity and competitor verification."""
        if not isinstance(tenant_id,str) or not tenant_id.strip():
            raise ValueError('Business required')
        result,reason=self.gate.evaluate(
            tenant_id=tenant_id,topic=topic,candidate=candidate,
            platform=platform,account_id=account_id,
            identity_verified=identity_verified,
            local_competitor_risk=local_competitor_risk)
        if result=='blocked':
            # Remove any earlier review entry when subsequent screening blocks it.
            with self.db:
                self.db.execute('DELETE FROM editorial_inbox WHERE tenant_id=? AND original_url=?',
                                (tenant_id,candidate.original_url))
            return 'blocked',reason
        # Even eligible content needs editorial review. Never enqueue as publish-ready.
        if urlparse(candidate.original_url).scheme!='https':
            return 'blocked','invalid_original_url'
        with self.db:
            self.db.execute("""INSERT INTO editorial_inbox VALUES (?,?,?,?,?,?,?,?)
                ON CONFLICT(tenant_id,original_url) DO UPDATE SET
                platform=excluded.platform,account_id=excluded.account_id,
                topic=excluded.topic,summary=excluded.summary,
                status=excluded.status,reason=excluded.reason""",
                (tenant_id,platform,account_id,candidate.original_url,topic,
                 candidate.summary,'review',reason))
        return 'review',reason

    def list_for_business(self, tenant_id):
        if not isinstance(tenant_id,str) or not tenant_id.strip():
            raise ValueError('Business required')
        return self.db.execute("""SELECT original_url,topic,summary,status,reason
            FROM editorial_inbox WHERE tenant_id=? ORDER BY original_url""",
            (tenant_id,)).fetchall()
