"""Offline workflow and audit trail. Intentionally has no network or publication code."""
import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, time, timezone
from zoneinfo import ZoneInfo

TZ = ZoneInfo('America/New_York')
DDL = '''
CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, at TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL, subject TEXT NOT NULL, details TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS approvals (post_id TEXT PRIMARY KEY, decision TEXT NOT NULL CHECK(decision IN ('approved','rejected','revoked')), actor TEXT NOT NULL, decided_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS discovered_events (id TEXT PRIMARY KEY, title TEXT NOT NULL, event_start TEXT NOT NULL, source_url TEXT NOT NULL, participation TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN ('unconfirmed','confirmed','rejected')), last_seen TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS outbox (post_id TEXT PRIMARY KEY, slot TEXT NOT NULL UNIQUE, payload_hash TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN ('prepared','cancelled')), prepared_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS workflow_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
INSERT OR IGNORE INTO workflow_settings VALUES ('dry_run_only','true');
INSERT OR IGNORE INTO workflow_settings VALUES ('paused','true');
'''

def setup(db):
    db.executescript(DDL)

def iso(dt):
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError('Timezone-aware datetime required')
    return dt.isoformat()

def audit(db, at, actor, action, subject, details=None):
    db.execute('INSERT INTO audit(at,actor,action,subject,details) VALUES (?,?,?,?,?)', (iso(at),actor,action,subject,json.dumps(details or {},sort_keys=True)))

def set_pause(db, *, paused, actor, at):
    # Safety-first: offline prototype cannot unpause publishing.
    if not paused:
        raise PermissionError('Unpausing requires a separately reviewed live integration')
    db.execute("UPDATE workflow_settings SET value='true' WHERE key='paused'")
    audit(db,at,actor,'pause','all')
    db.commit()

def record_approval(db, *, post_id, decision, actor, at):
    if decision not in ('approved','rejected','revoked') or not actor.strip():
        raise ValueError('Explicit decision and actor required')
    post=db.execute('SELECT status FROM posts WHERE id=?',(post_id,)).fetchone()
    if not post or post[0]=='blocked':
        raise ValueError('Cannot approve nonexistent or blocked post')
    db.execute('INSERT INTO approvals VALUES (?,?,?,?) ON CONFLICT(post_id) DO UPDATE SET decision=excluded.decision,actor=excluded.actor,decided_at=excluded.decided_at',(post_id,decision,actor,iso(at)))
    audit(db,at,actor,'post_'+decision,post_id)
    db.commit()

def upsert_discovery(db, *, title, event_start, source_url, participation, at):
    if not source_url.startswith(('https://','http://')) or not title.strip():
        raise ValueError('A named event and source URL are required')
    key=hashlib.sha256((source_url.strip().lower()+'\0'+iso(event_start)).encode()).hexdigest()
    db.execute('''INSERT INTO discovered_events VALUES (?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET last_seen=excluded.last_seen''', (key,title,iso(event_start),source_url,participation,'unconfirmed',iso(at)))
    audit(db,at,'discovery','event_seen',key,{'title':title})
    db.commit()
    return key

def decide_event(db, *, event_id, confirmed, actor, at):
    row=db.execute('SELECT id FROM discovered_events WHERE id=?',(event_id,)).fetchone()
    if not row: raise ValueError('Unknown event')
    db.execute('UPDATE discovered_events SET state=? WHERE id=?',('confirmed' if confirmed else 'rejected',event_id))
    audit(db,at,actor,'event_confirmed' if confirmed else 'event_rejected',event_id)
    db.commit()

def next_slots(start, days=7):
    """Generate exact local-wall-clock slots across DST changes, no naive UTC offset."""
    local=start.astimezone(TZ)
    for offset in range(days):
        day=local.date()+timedelta(days=offset)
        if day < local.date(): continue
        candidates=[('morning',time(10,0))]
        if day.weekday() in (0,2,4,5): candidates.append(('evening',time(18,30)))
        for kind,t in candidates:
            when=datetime.combine(day,t,tzinfo=TZ)
            if when >= local: yield kind,when

def prepare_dry_run(db, *, post_id, slot, at):
    """Persist a preview record only; no API client exists in this package."""
    if db.execute("SELECT value FROM workflow_settings WHERE key='dry_run_only'").fetchone() != ('true',):
        raise PermissionError('Dry-run guard missing')
    row=db.execute('SELECT content,status,authorization_id FROM posts WHERE id=?',(post_id,)).fetchone()
    if not row or row[1] in ('blocked','duplicate'): raise ValueError('Post not eligible')
    approval=db.execute('SELECT decision FROM approvals WHERE post_id=?',(post_id,)).fetchone()
    if approval and approval[0] in ('rejected','revoked'): raise PermissionError('Post rejected or revoked')
    if row[1]=='approval_required' and approval!=('approved',): raise PermissionError('Approval required')
    # Revalidate authorization expiry at the scheduled posting instant, not only staging time.
    if row[2]:
        auth=db.execute('SELECT starts_at,expires_at FROM authorizations WHERE id=?',(row[2],)).fetchone()
        if not auth or not (datetime.fromisoformat(auth[0]) <= slot <= datetime.fromisoformat(auth[1])):
            raise PermissionError('Authorization inactive at publication slot')
    if slot <= at: raise ValueError('Scheduled time must be in the future')
    payload_hash=hashlib.sha256(row[0].encode()).hexdigest()
    db.execute("INSERT INTO outbox VALUES (?,?,?,?,?)",(post_id,iso(slot),payload_hash,'prepared',iso(at)))
    audit(db,at,'system','dry_run_prepared',post_id,{'slot':iso(slot)})
    db.commit()
    return {'post_id':post_id,'slot':iso(slot),'mode':'DRY_RUN_ONLY'}

def cancel_preview(db, *, post_id, actor, at):
    db.execute("UPDATE outbox SET state='cancelled' WHERE post_id=?",(post_id,))
    audit(db,at,actor,'preview_cancelled',post_id)
    db.commit()
