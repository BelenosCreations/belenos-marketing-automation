import sqlite3
import unittest
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from posting_preferences import PostingPreferences

class PostingPreferenceTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.directory=AccountDirectory(self.db)
        self.directory.bootstrap_owner('shop','owner')
        self.directory.bootstrap_owner('other','other_owner')
        self.directory.set_member(Principal('owner','shop',Role.OWNER),
                                  'viewer',Role.VIEWER)
        self.sessions=SessionStore(self.db)
        self.owner=self.sessions.issue(Principal('owner','shop',Role.OWNER),now=100)
        self.viewer=self.sessions.issue(Principal('viewer','shop',Role.VIEWER),now=100)
        self.prefs=PostingPreferences(db=self.db,sessions=self.sessions,
            directory=self.directory)

    def set(self,**overrides):
        args=dict(token=self.owner,tenant_id='shop',mode='manual',
            timezone='America/New_York',manual_times=['18:30','10:00'],now=101)
        args.update(overrides)
        return self.prefs.set(**args)

    def test_unconfigured_does_not_claim_scheduling(self):
        result=self.prefs.get(token=self.owner,tenant_id='shop',now=101)
        self.assertFalse(result['configured'])
        self.assertIsNone(result['timezone'])
        self.assertFalse(result['publishing_enabled'])

    def test_manual_times_are_sorted(self):
        result=self.set()
        self.assertEqual(result['manual_times'],['10:00','18:30'])
        self.assertEqual(result['timezone'],'America/New_York')
        self.assertFalse(result['publishing_enabled'])

    def test_smart_keeps_no_fabricated_recommendations(self):
        result=self.set(mode='smart',manual_times=[])
        self.assertEqual(result['mode'],'smart')
        self.assertEqual(result['manual_times'],[])

    def test_cross_tenant_mutation_denied(self):
        with self.assertRaises(PermissionError):
            self.set(tenant_id='other')

    def test_viewer_cannot_modify(self):
        with self.assertRaises(PermissionError):
            self.set(token=self.viewer)
        self.assertFalse(self.prefs.get(token=self.viewer,
            tenant_id='shop',now=102)['configured'])

    def test_bad_times_and_timezone_rejected(self):
        for times in ([],['24:00'],['10:60'],['10:00','10:00'],
                      ['1:00'],['¹0:00'],['10:00']*25):
            with self.subTest(times=times):
                with self.assertRaises(ValueError):
                    self.set(manual_times=times)
        with self.assertRaises(ValueError):
            self.set(timezone='Not/A_Timezone')

    def test_smart_mode_rejects_hidden_manual_times(self):
        with self.assertRaises(ValueError):
            self.set(mode='smart',manual_times=['10:00'])
        with self.assertRaises(ValueError):
            self.set(mode=None)

    def test_preferences_survive_service_recreation(self):
        self.set()
        recreated=PostingPreferences(db=self.db,sessions=self.sessions,
            directory=self.directory)
        result=recreated.get(token=self.owner,tenant_id='shop',now=102)
        self.assertTrue(result['configured'])
        self.assertEqual(result['manual_times'],['10:00','18:30'])

    def test_revoked_session_denied(self):
        self.sessions.revoke(self.owner,now=101)
        with self.assertRaises(PermissionError):
            self.set(now=102)

if __name__=='__main__':unittest.main()
