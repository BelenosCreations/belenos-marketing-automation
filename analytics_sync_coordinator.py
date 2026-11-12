"""Offline analytics synchronization checkpoint and bounded batch coordinator.

No network or provider API access. A trusted adapter must supply the batch.
"""
import sqlite3

class AnalyticsSyncCoordinator:
    def __init__(self, *, db, importer):
        self.db=db
        self.importer=importer
        db.execute("""CREATE TABLE IF NOT EXISTS analytics_sync_checkpoints (
            tenant_id TEXT NOT NULL, platform TEXT NOT NULL,
            account_id TEXT NOT NULL, cursor TEXT NOT NULL,
            updated_at INTEGER NOT NULL,
            PRIMARY KEY (tenant_id,platform,account_id)
        )""")
        db.commit()

    def checkpoint(self, *, tenant_id, platform, account_id):
        row=self.db.execute("""SELECT cursor,updated_at
            FROM analytics_sync_checkpoints WHERE tenant_id=? AND platform=?
            AND account_id=?""",(tenant_id,platform,account_id)).fetchone()
        return None if row is None else {'cursor':row[0],'updated_at':row[1]}

    def apply_batch(self, *, tenant_id, platform, account_id, import_secret,
                    expected_cursor, next_cursor, observations, now,
                    admission_guard=None):
        if (type(now) is not int or now<0 or not isinstance(next_cursor,str)
                or not next_cursor or len(next_cursor)>512
                or (expected_cursor is not None and
                    (not isinstance(expected_cursor,str) or
                     not expected_cursor or len(expected_cursor)>512))):
            raise ValueError('Invalid checkpoint')
        if not isinstance(observations,(list,tuple)) or not 1<=len(observations)<=100:
            raise ValueError('Batch must contain 1 to 100 observations')
        if any(not isinstance(item,dict) or set(item)!={
                'source_post_id','candidate','engagement_count',
                'impression_count','measured_at'} for item in observations):
            raise ValueError('Invalid observation fields')
        if admission_guard is not None and not callable(admission_guard):
            raise TypeError('Trusted transactional admission guard required')
        # Authorize before reading or writing a checkpoint. Credentials come
        # from a trusted server integration, not from a mobile client.
        self.importer.authorize(tenant_id=tenant_id,platform=platform,
                                account_id=account_id,import_secret=import_secret)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            # The connection gate must be rechecked after provider fetch and
            # while this writer holds SQLite's exclusive write reservation.
            # If permission was revoked mid-fetch, no post or checkpoint lands.
            if admission_guard is not None:
                admission_guard()
            current=self.checkpoint(tenant_id=tenant_id,platform=platform,
                                    account_id=account_id)
            if (None if current is None else current['cursor'])!=expected_cursor:
                raise ValueError('Stale synchronization checkpoint')
            for item in observations:
                self.importer.import_observation(
                    tenant_id=tenant_id,platform=platform,account_id=account_id,
                    import_secret=import_secret,**item)
            self.db.execute("""INSERT INTO analytics_sync_checkpoints
                (tenant_id,platform,account_id,cursor,updated_at)
                VALUES (?,?,?,?,?)
                ON CONFLICT(tenant_id,platform,account_id) DO UPDATE SET
                cursor=excluded.cursor,updated_at=excluded.updated_at""",
                (tenant_id,platform,account_id,next_cursor,now))
        return {'imported':len(observations),'cursor':next_cursor,
                'publishing_enabled':False}
