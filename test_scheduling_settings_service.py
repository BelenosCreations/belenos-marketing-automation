import sqlite3
import unittest
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from scheduling_settings import SchedulingSettings
from scheduling_settings_service import SchedulingSettingsService
from posting_schedule_policy import SchedulePreferences

class SchedulingSettingsServiceTests(unittest.TestCase):
    def setUp(self):
        db=sqlite3.connect(':memory:')
        self.directory=AccountDirectory(db)
        self.directory.bootstrap_owner('shop','owner')
        self.directory.bootstrap_owner('other','otherowner')
        self.directory.set_member(Principal('owner','shop',Role.OWNER),
                                  'viewer',Role.VIEWER)
        self.sessions=SessionStore(db)
        self.owner=self.sessions.issue(Principal('owner','shop',Role.OWNER),now=100)
        self.viewer=self.sessions.issue(Principal('viewer','shop',Role.VIEWER),now=100)
        self.other=self.sessions.issue(Principal('otherowner','other',Role.OWNER),now=100)
        self.service=SchedulingSettingsService(settings=SchedulingSettings(db,self.directory),
            sessions=self.sessions,directory=self.directory)
        self.prefs=SchedulePreferences('manual','America/New_York',{1:['11:17']})

    def test_owner_can_save_and_read(self):
        self.assertEqual(self.service.save(token=self.owner,tenant_id='shop',
            preferences=self.prefs,now=101),1)
        self.assertEqual(self.service.get(token=self.owner,tenant_id='shop',
            now=102)['preferences'],self.prefs)

    def test_viewer_can_read_but_not_write(self):
        self.service.save(token=self.owner,tenant_id='shop',preferences=self.prefs,now=101)
        self.assertEqual(self.service.get(token=self.viewer,tenant_id='shop',
            now=102)['revision'],1)
        with self.assertRaises(PermissionError):
            self.service.save(token=self.viewer,tenant_id='shop',
                preferences=self.prefs,now=102)

    def test_cross_tenant_denied(self):
        with self.assertRaises(PermissionError):
            self.service.get(token=self.owner,tenant_id='other',now=101)

    def test_expired_token_denied(self):
        with self.assertRaises(PermissionError):
            self.service.get(token=self.owner,tenant_id='shop',now=4000)

    def test_revoked_token_denied(self):
        self.sessions.revoke(self.owner,now=101)
        with self.assertRaises(PermissionError):
            self.service.save(token=self.owner,tenant_id='shop',
                preferences=self.prefs,now=102)

    def test_membership_revocation_denied(self):
        self.directory.set_member(Principal('owner','shop',Role.OWNER),
            'viewer',Role.VIEWER,active=False)
        with self.assertRaises(PermissionError):
            self.service.get(token=self.viewer,tenant_id='shop',now=102)

    def test_promoted_viewer_requires_fresh_session_before_writing(self):
        self.directory.set_member(
            Principal('owner','shop',Role.OWNER),'viewer',Role.OWNER)
        with self.assertRaises(PermissionError):
            self.service.save(token=self.viewer,tenant_id='shop',
                preferences=self.prefs,now=102)
        fresh=self.sessions.issue(
            Principal('viewer','shop',Role.OWNER),now=100)
        self.assertEqual(self.service.save(token=fresh,
            tenant_id='shop',preferences=self.prefs,now=102),1)

    def test_revision_conflict(self):
        self.service.save(token=self.owner,tenant_id='shop',
            preferences=self.prefs,expected_revision=0,now=101)
        with self.assertRaises(ValueError):
            self.service.save(token=self.owner,tenant_id='shop',
                preferences=self.prefs,expected_revision=0,now=102)

if __name__=='__main__':unittest.main()
