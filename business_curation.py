"""Business-specific third-party source curation, offline only.

A source's approval for one business never grants approval for another.
Industry tags are business-owned and must match the source classification.
"""
import sqlite3
from urllib.parse import urlparse
from optimizer import Candidate, curate

class BusinessCuration:
    def __init__(self, db: sqlite3.Connection):
        self.db=db
        db.execute("""CREATE TABLE IF NOT EXISTS business_profiles (
            tenant_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            industry TEXT NOT NULL
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS business_topics (
            tenant_id TEXT NOT NULL,
            topic TEXT NOT NULL,
            PRIMARY KEY (tenant_id,topic),
            FOREIGN KEY (tenant_id) REFERENCES business_profiles(tenant_id)
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS business_sources (
            tenant_id TEXT NOT NULL,
            source_url TEXT NOT NULL,
            source_name TEXT NOT NULL,
            topic TEXT NOT NULL,
            approved INTEGER NOT NULL CHECK(approved IN (0,1)),
            PRIMARY KEY (tenant_id,source_url),
            FOREIGN KEY (tenant_id,topic) REFERENCES business_topics(tenant_id,topic)
        )""")
        db.commit()

    @staticmethod
    def _valid(*values):
        if any(not isinstance(v,str) or not v.strip() for v in values):
            raise ValueError('Nonempty values required')

    def create_profile(self, tenant_id, display_name, industry, topics):
        self._valid(tenant_id,display_name,industry)
        topics=list(topics)
        if not topics or any(not isinstance(t,str) or not t.strip() for t in topics):
            raise ValueError('At least one valid topic required')
        with self.db:
            self.db.execute('INSERT INTO business_profiles VALUES (?,?,?)',
                            (tenant_id,display_name,industry))
            self.db.executemany('INSERT INTO business_topics VALUES (?,?)',
                                [(tenant_id,t) for t in set(topics)])

    def add_source(self, *, tenant_id, source_url, source_name, topic, approved=False):
        """Trusted admin configuration, not a client-authorized endpoint."""
        self._valid(tenant_id,source_url,source_name,topic)
        parsed=urlparse(source_url)
        if parsed.scheme!='https' or not parsed.netloc:
            raise ValueError('HTTPS source required')
        if not self.db.execute('SELECT 1 FROM business_topics WHERE tenant_id=? AND topic=?',
                               (tenant_id,topic)).fetchone():
            raise PermissionError('Topic not enabled for business')
        with self.db:
            self.db.execute("""INSERT INTO business_sources VALUES (?,?,?,?,?)
                ON CONFLICT(tenant_id,source_url) DO UPDATE SET
                source_name=excluded.source_name,topic=excluded.topic,approved=excluded.approved""",
                (tenant_id,source_url,source_name,topic,int(bool(approved))))

    def evaluate(self, *, tenant_id, topic, candidate: Candidate):
        """Fail closed on missing business, topic or matching approved source."""
        if not isinstance(tenant_id,str) or not isinstance(topic,str):
            return 'blocked','missing_business_or_topic'
        source=self.db.execute("""SELECT approved FROM business_sources
            WHERE tenant_id=? AND source_url=? AND topic=?""",
            (tenant_id,candidate.source_url,topic)).fetchone()
        if source is None:
            return 'approval_required','source_not_configured_for_business'
        if not source[0]:
            return 'approval_required','source_not_approved_for_business'
        if not candidate.source_approved:
            return 'approval_required','source_verification_missing'
        return curate(candidate)
