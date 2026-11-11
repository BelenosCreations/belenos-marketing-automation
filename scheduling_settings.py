"""Per-business persisted posting-time preferences.

Offline repository only; callers must pass an authenticated principal through
the existing directory. This never schedules or publishes a post.
"""
import json
from access_policy import Action,Principal
from posting_schedule_policy import SchedulePreferences

class SchedulingSettings:
    def __init__(self, db, directory):
        self.db=db
        self.directory=directory
        db.execute("""CREATE TABLE IF NOT EXISTS scheduling_settings (
            tenant_id TEXT PRIMARY KEY,
            mode TEXT NOT NULL,
            timezone_name TEXT NOT NULL,
            weekly_json TEXT NOT NULL,
            preferred_hours_json TEXT NOT NULL,
            revision INTEGER NOT NULL DEFAULT 1
        )""")
        db.commit()

    def _authorize(self, principal, tenant_id, write):
        action=Action.EDIT_DRAFT if write else Action.READ_DRAFTS
        if not self.directory.authorize(principal,action,tenant_id):
            raise PermissionError('Business scheduling access denied')

    def get(self, *, principal, tenant_id):
        self._authorize(principal,tenant_id,False)
        row=self.db.execute("""SELECT mode,timezone_name,weekly_json,
            preferred_hours_json,revision FROM scheduling_settings
            WHERE tenant_id=?""",(tenant_id,)).fetchone()
        if row is None:
            return None
        prefs=SchedulePreferences(mode=row[0],timezone_name=row[1],
            manual_weekly={int(k):v for k,v in json.loads(row[2]).items()},
            preferred_hours=tuple(json.loads(row[3])))
        return {'preferences':prefs,'revision':row[4]}

    def save(self, *, principal, tenant_id, preferences, expected_revision=None):
        self._authorize(principal,tenant_id,True)
        if not isinstance(preferences,SchedulePreferences):
            raise ValueError('Invalid scheduling preferences')
        if expected_revision is not None and (type(expected_revision) is not int
                                               or expected_revision<0):
            raise ValueError('Invalid expected revision')
        with self.db:
            current=self.db.execute("""SELECT revision FROM scheduling_settings
                WHERE tenant_id=?""",(tenant_id,)).fetchone()
            revision=current[0] if current else 0
            if expected_revision is not None and revision!=expected_revision:
                raise ValueError('Scheduling settings were modified by another user')
            self.db.execute("""INSERT INTO scheduling_settings
                (tenant_id,mode,timezone_name,weekly_json,preferred_hours_json,revision)
                VALUES (?,?,?,?,?,?)
                ON CONFLICT(tenant_id) DO UPDATE SET
                mode=excluded.mode,timezone_name=excluded.timezone_name,
                weekly_json=excluded.weekly_json,
                preferred_hours_json=excluded.preferred_hours_json,
                revision=excluded.revision""",
                (tenant_id,preferences.mode,preferences.timezone_name,
                 json.dumps(preferences.manual_weekly,sort_keys=True),
                 json.dumps(preferences.preferred_hours),revision+1))
        return revision+1
