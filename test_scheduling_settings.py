import sqlite3
import unittest
from access_policy import Principal,Role
from accounts import AccountDirectory
from scheduling_settings import SchedulingSettings
from posting_schedule_policy import SchedulePreferences

class SchedulingSettingsTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.directory=AccountDirectory(self.db)
        self.directory.bootstrap_owner('shop','owner')
        self.directory.bootstrap_owner('other','otherowner')
        self.owner=Principal('owner','shop',Role.OWNER)
        self.other=Principal('otherowner','other',Role.OWNER)
        self.directory.set_member(self.owner,'viewer',Role.VIEWER)
        self.viewer=Principal('viewer','shop',Role.VIEWER)
        self.settings=SchedulingSettings(self.db,self.directory)
        self.manual=SchedulePreferences('manual','America/New_York',
            {1:['10:00','11:17'],4:['18:30']})

    def test_roundtrip(self):
        self.assertEqual(self.settings.save(principal=self.owner,
            tenant_id='shop',preferences=self.manual),1)
        result=self.settings.get(principal=self.owner,tenant_id='shop')
        self.assertEqual(result['preferences'].manual_weekly,self.manual.manual_weekly)
        self.assertEqual(result['preferences'].mode,'manual')

    def test_smart_roundtrip(self):
        smart=SchedulePreferences('smart','America/Chicago',{},
            preferred_hours=(9,15,20))
        self.settings.save(principal=self.owner,tenant_id='shop',preferences=smart)
        self.assertEqual(self.settings.get(principal=self.owner,
            tenant_id='shop')['preferences'],smart)

    def test_tenant_isolation(self):
        self.settings.save(principal=self.owner,tenant_id='shop',preferences=self.manual)
        with self.assertRaises(PermissionError):
            self.settings.get(principal=self.owner,tenant_id='other')
        self.assertIsNone(self.settings.get(principal=self.other,tenant_id='other'))

    def test_viewer_can_read(self):
        self.settings.save(principal=self.owner,tenant_id='shop',preferences=self.manual)
        self.assertEqual(self.settings.get(principal=self.viewer,
            tenant_id='shop')['revision'],1)

    def test_viewer_cannot_write(self):
        with self.assertRaises(PermissionError):
            self.settings.save(principal=self.viewer,tenant_id='shop',
                preferences=self.manual)

    def test_stale_revision_rejected(self):
        self.settings.save(principal=self.owner,tenant_id='shop',
            preferences=self.manual,expected_revision=0)
        with self.assertRaises(ValueError):
            self.settings.save(principal=self.owner,tenant_id='shop',
                preferences=self.manual,expected_revision=0)

    def test_revision_increments(self):
        self.settings.save(principal=self.owner,tenant_id='shop',preferences=self.manual)
        self.assertEqual(self.settings.save(principal=self.owner,
            tenant_id='shop',preferences=self.manual,expected_revision=1),2)

    def test_deactivated_user_denied(self):
        self.directory.set_member(self.owner,'viewer',Role.VIEWER,active=False)
        with self.assertRaises(PermissionError):
            self.settings.get(principal=self.viewer,tenant_id='shop')

    def test_invalid_preferences_rejected(self):
        with self.assertRaises(ValueError):
            self.settings.save(principal=self.owner,tenant_id='shop',
                preferences={'mode':'smart'})

if __name__=='__main__':unittest.main()
