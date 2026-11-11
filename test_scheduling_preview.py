import sqlite3
import unittest
from datetime import datetime,timezone
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from scheduling_settings import SchedulingSettings
from scheduling_settings_service import SchedulingSettingsService
from posting_schedule_policy import SchedulePreferences,PostContext
from business_scheduling_planner import BusinessSchedulingPlanner
from scheduling_preview import SchedulingPreview

class SchedulingPreviewTests(unittest.TestCase):
    def setUp(self):
        db=sqlite3.connect(':memory:')
        directory=AccountDirectory(db)
        directory.bootstrap_owner('shop','owner')
        directory.bootstrap_owner('other','otherowner')
        sessions=SessionStore(db)
        self.owner=sessions.issue(Principal('owner','shop',Role.OWNER),now=100)
        self.other=sessions.issue(Principal('otherowner','other',Role.OWNER),now=100)
        settings=SchedulingSettingsService(
            settings=SchedulingSettings(db,directory),
            sessions=sessions,directory=directory)
        self.settings=settings
        self.preview=SchedulingPreview(business_planner=BusinessSchedulingPlanner(
            settings_service=settings))
        self.start=datetime(2026,11,10,15,tzinfo=timezone.utc)
        self.ready=PostContext('product','families','facebook',True,True)

    def run_preview(self,posts=None,**changes):
        args=dict(token=self.owner,tenant_id='shop',posts=posts or [self.ready],
                  start_utc=self.start,now=101)
        args.update(changes)
        return self.preview.preview(**args)

    def test_unconfigured(self):
        self.assertEqual(self.run_preview()['status'],'not_configured')

    def test_manual_preview_does_not_publish(self):
        self.settings.save(token=self.owner,tenant_id='shop',
            preferences=SchedulePreferences('manual','America/New_York',
                {1:['11:17','11:30']}),now=101)
        result=self.run_preview(posts=[self.ready,self.ready])
        self.assertEqual(result['items'][0]['scheduled_at'],
                         '2026-11-10T11:17:00-05:00')
        self.assertEqual(result['items'][1]['scheduled_at'],
                         '2026-11-10T11:30:00-05:00')
        self.assertFalse(result['publishing_enabled'])

    def test_held_post_not_proposed(self):
        self.settings.save(token=self.owner,tenant_id='shop',
            preferences=SchedulePreferences('smart','America/New_York',{}),now=101)
        result=self.run_preview(posts=[
            PostContext('product','families','facebook',False,False),self.ready])
        self.assertEqual(result['items'][0]['status'],'held')
        self.assertEqual(result['items'][1]['status'],'proposed')

    def test_cross_tenant_denied(self):
        with self.assertRaises(PermissionError):
            self.run_preview(tenant_id='other')

    def test_expired_session_denied(self):
        with self.assertRaises(PermissionError):
            self.run_preview(now=4000)

    def test_invalid_post_count(self):
        with self.assertRaises(ValueError):
            self.run_preview(posts=[self.ready]*31)

if __name__=='__main__':unittest.main()
