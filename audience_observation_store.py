"""Offline analytics observation store; ingestion requires trusted server caller.

No external provider connection or proof of source authenticity is implemented.
"""
import math
import sqlite3

class AudienceObservationStore:
    def __init__(self, db: sqlite3.Connection):
        self.db=db
        db.execute("""CREATE TABLE IF NOT EXISTS audience_observations (
            tenant_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            source_post_id TEXT NOT NULL,
            candidate TEXT NOT NULL,
            engagement_rate REAL NOT NULL,
            measured_at INTEGER NOT NULL,
            source_name TEXT NOT NULL,
            PRIMARY KEY (tenant_id,platform,source_post_id)
        )""")
        db.commit()

    def ingest_trusted(self, *, tenant_id, platform, source_post_id,
                       candidate, engagement_rate, measured_at, source_name):
        """Server-only method; never expose directly to untrusted app clients."""
        values=(tenant_id,platform,source_post_id,candidate,source_name)
        if any(not isinstance(v,str) or not v.strip() or len(v)>256 for v in values):
            raise ValueError('Invalid observation identity')
        if (type(engagement_rate) not in (int,float)
                or not math.isfinite(engagement_rate)
                or not 0<=engagement_rate<=1):
            raise ValueError('Invalid engagement rate')
        if type(measured_at) is not int or measured_at<0:
            raise ValueError('Invalid measurement timestamp')
        already_in_transaction=self.db.in_transaction
        self.db.execute("""INSERT INTO audience_observations
                (tenant_id,platform,source_post_id,candidate,engagement_rate,
                 measured_at,source_name) VALUES (?,?,?,?,?,?,?)""",
                (tenant_id,platform,source_post_id,candidate,
                 float(engagement_rate),measured_at,source_name))
        if not already_in_transaction:
            self.db.commit()
        return {'stored':True,'publishing_enabled':False}

    def for_candidates(self, *, tenant_id, platform, candidates,
                       since, until, limit=1000):
        if (not isinstance(tenant_id,str) or not tenant_id.strip()
                or not isinstance(platform,str) or not platform.strip()):
            raise ValueError('Tenant and platform required')
        if (not isinstance(candidates,(list,tuple)) or not 1<=len(candidates)<=20
                or any(not isinstance(c,str) or not c for c in candidates)
                or len(set(candidates))!=len(candidates)):
            raise ValueError('Unique candidates required')
        if (type(since) is not int or type(until) is not int
                or since<0 or until<since):
            raise ValueError('Invalid observation window')
        if type(limit) is not int or not 1<=limit<=1000:
            raise ValueError('Invalid query limit')
        placeholders=','.join('?' for _ in candidates)
        rows=self.db.execute(
            'SELECT candidate,engagement_rate FROM audience_observations '
            'WHERE tenant_id=? AND platform=? AND measured_at>=? '
            'AND measured_at<=? AND candidate IN ('+placeholders+') '
            'ORDER BY measured_at DESC,source_post_id LIMIT ?',
            (tenant_id,platform,since,until,*candidates,limit)).fetchall()
        return [dict(tenant_id=tenant_id,candidate=c,
                     engagement_rate=rate) for c,rate in rows]
