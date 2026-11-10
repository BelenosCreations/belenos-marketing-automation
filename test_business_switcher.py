import sqlite3
import unittest
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from business_curation import BusinessCuration
from business_switcher import BusinessSwitcher

class SwitcherTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.directory=AccountDirectory(self.db)
        self.directory.bootstrap_owner('belenos','owner')
        self.directory.bootstrap_owner('busy_b','busy_owner')
        self.directory.set_member(Principal('busy_owner','busy_b',Role.OWNER),'owner',Role.MARKETING_MANAGER)
        self.sessions=SessionStore(self.db)
        self.token=self.sessions.issue(Principal('owner','belenos',Role.OWNER),now=100)
        self.other_token=self.sessions.issue(Principal('busy_owner','busy_b',Role.OWNER),now=100)
        self.curation=BusinessCuration(self.db)
        self.curation.create_profile('belenos','Belenos Creations','custom printing',['3d_printing'])
        self.curation.create_profile('busy_b','Busy B Cleaning','commercial cleaning',['facility_care'])
        self.switcher=BusinessSwitcher(self.db,self.sessions,self.directory)

    def test_activation_issues_target_business_session(self):
        result=self.switcher.activate_business(token=self.token,
            tenant_id='busy_b',now=101)
        session=self.sessions.resolve(result['token'],now=102)
        self.assertEqual(session.principal.tenant_id,'busy_b')
        self.assertEqual(session.principal.role,Role.MARKETING_MANAGER)
        self.assertFalse(result['publishing_enabled'])

    def test_activation_cannot_cross_to_unjoined_business(self):
        with self.assertRaises(PermissionError):
            self.switcher.activate_business(token=self.token,
                tenant_id='unknown',now=101)

    def test_removed_source_membership_blocks_switch(self):
        self.db.execute('UPDATE members SET active=0 WHERE tenant_id=? AND subject_id=?',
                        ('belenos','owner'))
        self.db.commit()
        with self.assertRaises(PermissionError):
            self.switcher.activate_business(token=self.token,
                tenant_id='busy_b',now=101)

    def test_stale_source_role_cannot_switch(self):
        self.db.execute("UPDATE members SET role=? WHERE tenant_id=? AND subject_id=?",
                        (Role.VIEWER.value,'belenos','owner'))
        self.db.commit()
        with self.assertRaises(PermissionError):
            self.switcher.activate_business(token=self.token,tenant_id='busy_b',now=101)

    def test_one_login_lists_both_businesses(self):
        names=[x['display_name'] for x in self.switcher.list_businesses(token=self.token,now=101)]
        self.assertEqual(names,['Belenos Creations','Busy B Cleaning'])

    def test_role_per_business(self):
        result=self.switcher.select_business(token=self.token,tenant_id='busy_b',now=101)
        self.assertEqual(result['role'],'marketing_manager')

    def test_other_owner_only_own_business(self):
        result=self.switcher.list_businesses(token=self.other_token,now=101)
        self.assertEqual([x['tenant_id'] for x in result],['busy_b'])

    def test_removed_membership_disappears(self):
        self.directory.set_member(Principal('busy_owner','busy_b',Role.OWNER),'owner',Role.MARKETING_MANAGER,active=False)
        self.assertEqual([x['tenant_id'] for x in self.switcher.list_businesses(token=self.token,now=101)],['belenos'])

    def test_cannot_select_removed_business(self):
        self.directory.set_member(Principal('busy_owner','busy_b',Role.OWNER),'owner',Role.VIEWER,active=False)
        with self.assertRaises(PermissionError):
            self.switcher.select_business(token=self.token,tenant_id='busy_b',now=101)

    def test_unknown_business_denied(self):
        with self.assertRaises(PermissionError):
            self.switcher.select_business(token=self.token,tenant_id='unknown',now=101)

    def test_expired_session_denied(self):
        with self.assertRaises(PermissionError):
            self.switcher.list_businesses(token=self.token,now=4000)

    def test_unknown_token_denied(self):
        with self.assertRaises(PermissionError):
            self.switcher.select_business(token='invalid',tenant_id='belenos',now=101)

if __name__=='__main__': unittest.main()
