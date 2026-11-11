import sqlite3
import unittest
from datetime import datetime,timezone
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from posting_schedule_policy import SchedulePreferences,PostContext
from scheduling_settings import SchedulingSettings
from scheduling_settings_service import SchedulingSettingsService
from business_scheduling_planner import BusinessSchedulingPlanner

class BusinessPlannerTests(unittest.TestCase):
    def setUp(self):
        db=sqlite3.connect(':memory:')
        directory=AccountDirectory(db)
        directory.bootstrap_owner('shop','owner')
        directory.bootstrap_owner('other','otherowner')
        sessions=SessionStore(db)
        self.owner=sessions.issue(Principal('owner','shop',Role.OWNER),now=100)
        self.other=sessions.issue(Principal('otherowner','other',Role.OWNER),now=100)
        self.settings=SchedulingSettingsService(
            settings=SchedulingSettings(db,directory),sessions=sessions,directory=directory)
        self.planner=BusinessSchedulingPlanner(settings_service=self.settings)
        self.start=datetime(2026,11,10,15,0,tzinfo=timezone.utc)
        self.post=PostContext('New product','local families','facebook',True,True)

    def propose(self, **changes):
        args=dict(token=self.owner,tenant_id='shop',post=self.post,
                  start_utc=self.start,now=101)
        args.update(changes)
        return self.planner.propose(**args)

    def test_not_configured(self):
        self.assertEqual(self.propose()['status'],'not_configured')

    def test_saved_manual_exact_time(self):
        self.settings.save(token=self.owner,tenant_id='shop',
            preferences=SchedulePreferences('manual','America/New_York',
                {1:['11:17']}),now=101)
        result=self.propose()
        self.assertEqual(result['scheduled_at'],'2026-11-10T11:17:00-05:00')
        self.assertEqual(result['mode'],'manual')
        self.assertFalse(result['publishing_enabled'])

    def test_saved_smart(self):
        self.settings.save(token=self.owner,tenant_id='shop',
            preferences=SchedulePreferences('smart','America/New_York',{}),now=101)
        self.assertEqual(self.propose()['mode'],'smart')

    def test_cross_business_denied(self):
        with self.assertRaises(PermissionError):
            self.propose(tenant_id='other')

    def test_incomplete_post_held(self):
        self.settings.save(token=self.owner,tenant_id='shop',
            preferences=SchedulePreferences('smart','America/New_York',{}),now=101)
        result=self.propose(post=PostContext('product','families','facebook',False,True))
        self.assertEqual(result['status'],'held')

    def test_expired_session_denied(self):
        with self.assertRaises(PermissionError):
            self.propose(now=4000)

    def test_revision_included(self):
        self.settings.save(token=self.owner,tenant_id='shop',
            preferences=SchedulePreferences('smart','America/New_York',{}),now=101)
        self.assertEqual(self.propose()['settings_revision'],1)

if __name__=='__main__':unittest.main()
