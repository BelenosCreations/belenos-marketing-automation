import sqlite3
import unittest
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from scheduling_settings import SchedulingSettings
from scheduling_settings_service import SchedulingSettingsService
from scheduling_settings_view import SchedulingSettingsView

class SchedulingSettingsViewTests(unittest.TestCase):
    def setUp(self):
        db=sqlite3.connect(':memory:')
        directory=AccountDirectory(db)
        directory.bootstrap_owner('shop','owner')
        directory.bootstrap_owner('other','otherowner')
        directory.set_member(Principal('owner','shop',Role.OWNER),'viewer',Role.VIEWER)
        sessions=SessionStore(db)
        self.owner=sessions.issue(Principal('owner','shop',Role.OWNER),now=100)
        self.viewer=sessions.issue(Principal('viewer','shop',Role.VIEWER),now=100)
        self.view=SchedulingSettingsView(SchedulingSettingsService(
            settings=SchedulingSettings(db,directory),sessions=sessions,
            directory=directory))
        self.payload={'mode':'manual','timezone':'America/New_York',
            'manual_weekly':{'1':['11:17'],'4':['18:30']},
            'preferred_hours':[9,12,17]}

    def test_unconfigured_modes(self):
        data=self.view.load(token=self.owner,tenant_id='shop',now=101)
        self.assertFalse(data['configured'])
        self.assertEqual(data['available_modes'],['manual','smart'])

    def test_roundtrip(self):
        result=self.view.save(token=self.owner,tenant_id='shop',
            payload=self.payload,now=101)
        self.assertEqual(result['revision'],1)
        data=self.view.load(token=self.owner,tenant_id='shop',now=102)
        self.assertEqual(data['manual_weekly']['1'],['11:17'])
        self.assertFalse(data['publishing_enabled'])

    def test_smart_switch(self):
        self.view.save(token=self.owner,tenant_id='shop',payload=self.payload,now=101)
        payload=dict(self.payload,mode='smart',expected_revision=1)
        self.assertEqual(self.view.save(token=self.owner,tenant_id='shop',
            payload=payload,now=102)['revision'],2)

    def test_viewer_read_only(self):
        self.view.save(token=self.owner,tenant_id='shop',payload=self.payload,now=101)
        self.assertTrue(self.view.load(token=self.viewer,tenant_id='shop',now=102)['configured'])
        with self.assertRaises(PermissionError):
            self.view.save(token=self.viewer,tenant_id='shop',payload=self.payload,now=102)

    def test_cross_tenant_denied(self):
        with self.assertRaises(PermissionError):
            self.view.load(token=self.owner,tenant_id='other',now=101)

    def test_unexpected_fields_rejected(self):
        with self.assertRaises(ValueError):
            self.view.save(token=self.owner,tenant_id='shop',
                payload=dict(self.payload,publish_now=True),now=101)

    def test_stale_revision_rejected(self):
        self.view.save(token=self.owner,tenant_id='shop',payload=self.payload,now=101)
        with self.assertRaises(ValueError):
            self.view.save(token=self.owner,tenant_id='shop',
                payload=dict(self.payload,expected_revision=0),now=102)

if __name__=='__main__':unittest.main()
