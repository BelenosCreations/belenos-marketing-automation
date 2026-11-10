"""Belenos marketing policy engine. Offline only: no publishing or network calls."""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import sqlite3

@dataclass(frozen=True)
class Decision:
    status: str
    reason: str

SCHEMA = '''
CREATE TABLE IF NOT EXISTS authorizations (
 id TEXT PRIMARY KEY, kind TEXT NOT NULL, exact_terms TEXT NOT NULL,
 starts_at TEXT NOT NULL, expires_at TEXT NOT NULL, approved_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS posts (
 id TEXT PRIMARY KEY, slot TEXT NOT NULL, content TEXT NOT NULL,
 classification TEXT NOT NULL, authorization_id TEXT,
 status TEXT NOT NULL, reason TEXT NOT NULL,
 created_at TEXT NOT NULL, UNIQUE(slot, content)
);
CREATE TABLE IF NOT EXISTS delivery_attempts (
 id INTEGER PRIMARY KEY AUTOINCREMENT, post_id TEXT NOT NULL,
 provider TEXT NOT NULL, external_id TEXT, status TEXT NOT NULL,
 recorded_at TEXT NOT NULL, UNIQUE(post_id, provider)
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
INSERT OR IGNORE INTO settings VALUES ('publishing_enabled', 'false');
'''

def initialize(db):
    db.executescript(SCHEMA)

def normalize(s):
    return ' '.join(s.casefold().split())

def classify(db, *, content, category, now, authorization_id=None, verified=True):
    if not verified:
        return Decision('blocked', 'Unverified claim or incorrect details')
    if category == 'invented_offer':
        return Decision('blocked', 'Offers cannot be invented')
    if category == 'community':
        return Decision('auto_eligible', 'Routine community content')
    if authorization_id:
        row = db.execute('SELECT exact_terms, starts_at, expires_at FROM authorizations WHERE id=?', (authorization_id,)).fetchone()
        if row and row[1] <= now.isoformat() <= row[2] and normalize(row[0]) in normalize(content):
            return Decision('auto_eligible', 'Active user-authorized terms included unchanged')
        return Decision('approval_required', 'Authorization absent, expired, or terms differ')
    return Decision('approval_required', 'New event, product, or promotional claim')

def stage(db, *, slot, content, category, now, authorization_id=None, verified=True):
    key = hashlib.sha256((slot+'\0'+normalize(content)).encode()).hexdigest()
    existing = db.execute('SELECT status, reason FROM posts WHERE id=?', (key,)).fetchone()
    if existing:
        return key, Decision('duplicate', 'Already staged for this slot')
    decision = classify(db, content=content, category=category, now=now,
                        authorization_id=authorization_id, verified=verified)
    db.execute('INSERT INTO posts VALUES (?,?,?,?,?,?,?,?)',
               (key,slot,content,category,authorization_id,decision.status,decision.reason,now.isoformat()))
    db.commit()
    return key, decision

def may_publish(db, post_id):
    enabled = db.execute("SELECT value FROM settings WHERE key='publishing_enabled'").fetchone()
    row = db.execute('SELECT status FROM posts WHERE id=?',(post_id,)).fetchone()
    return bool(enabled and enabled[0]=='true' and row and row[0] in ('auto_eligible','approved'))

if __name__ == '__main__':
    db = sqlite3.connect(':memory:')
    initialize(db)
    now = datetime(2026,11,10,12,tzinfo=timezone.utc)
    for category,content in [('community','What holiday tradition do you love?'),('invented_offer','20% off everything'),('promotion','A brand new tumbler is available')]:
        print(category, stage(db,slot='2026-11-11T18:30:00-05:00',content=content,category=category,now=now)[1])
