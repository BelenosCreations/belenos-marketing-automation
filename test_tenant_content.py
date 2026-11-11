import sqlite3
import unittest
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from tenant_content import TenantContentStore
from tenant_approval_service import TenantApprovalService

class TenantNativeTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.execute('PRAGMA foreign_keys=ON')
        self.directory=AccountDirectory(self.db)
        self.directory.bootstrap_owner('belenos','owner')
        self.directory.bootstrap_owner('other','otherowner')
        self.owner=Principal('owner','belenos',Role.OWNER)
        self.directory.set_member(self.owner,'manager',Role.MARKETING_MANAGER)
        self.sessions=SessionStore(self.db)
        self.owner_token=self.sessions.issue(self.owner,now=100)
        self.other_token=self.sessions.issue(Principal('otherowner','other',Role.OWNER),now=100)
        self.manager_token=self.sessions.issue(Principal('manager','belenos',Role.MARKETING_MANAGER),now=100)
        self.service=TenantApprovalService(self.db,self.sessions,self.directory)
        self.content=self.service.content
        self.content.create_post('belenos','shared','Product announcement','promotion')
        self.content.create_post('other','shared','Different business','promotion')
        self.content.create_post('belenos','routine','Favorite print?','community')

    def test_same_post_id_isolated(self):
        self.service.decide_post(token=self.owner_token,tenant_id='belenos',post_id='shared',decision='approved',now=101)
        self.assertEqual(self.content.get_post('belenos','shared')[2],'approved')
        self.assertEqual(self.content.get_post('other','shared')[2],'approval_required')

    def test_other_owner_cannot_approve_belenos(self):
        with self.assertRaises(PermissionError):
            self.service.decide_post(token=self.other_token,tenant_id='belenos',post_id='shared',decision='approved',now=101)

    def test_manager_cannot_approve_promo(self):
        with self.assertRaises(PermissionError):
            self.service.decide_post(token=self.manager_token,tenant_id='belenos',post_id='shared',decision='approved',now=101)

    def test_manager_can_approve_routine(self):
        self.service.decide_post(token=self.manager_token,tenant_id='belenos',post_id='routine',decision='approved',now=101)
        self.assertEqual(self.content.get_post('belenos','routine')[2],'approved')

    def test_manager_cannot_revoke_routine(self):
        with self.assertRaises(PermissionError):
            self.service.decide_post(token=self.manager_token,tenant_id='belenos',post_id='routine',decision='revoked',now=101)

    def test_unknown_post_denied(self):
        with self.assertRaises(PermissionError):
            self.service.decide_post(token=self.owner_token,tenant_id='belenos',post_id='missing',decision='approved',now=101)

    def test_role_upgrade_requires_current_session_for_approval(self):
        self.directory.set_member(self.owner,'manager',Role.OWNER)
        with self.assertRaises(PermissionError):
            self.service.decide_post(token=self.manager_token,
                tenant_id='belenos',post_id='shared',
                decision='approved',now=101)
        current=self.sessions.issue(
            Principal('manager','belenos',Role.OWNER),now=100)
        self.service.decide_post(token=current,
            tenant_id='belenos',post_id='shared',
            decision='approved',now=101)
        self.assertEqual(self.content.get_post('belenos','shared')[2],
                         'approved')

    def test_role_change_rechecked(self):
        self.directory.set_member(self.owner,'manager',Role.VIEWER)
        with self.assertRaises(PermissionError):
            self.service.decide_post(token=self.manager_token,tenant_id='belenos',post_id='routine',decision='approved',now=101)

    def test_expired_session_denied(self):
        with self.assertRaises(PermissionError):
            self.service.decide_post(token=self.owner_token,tenant_id='belenos',post_id='shared',decision='approved',now=4000)

    def test_event_isolation(self):
        self.content.create_event('belenos','expo','Belenos expo')
        self.content.create_event('other','expo','Other expo')
        self.service.decide_event(token=self.owner_token,tenant_id='belenos',event_id='expo',confirmed=True,now=101)
        self.assertEqual(self.content.get_event('belenos','expo')[1],'confirmed')
        self.assertEqual(self.content.get_event('other','expo')[1],'unconfirmed')

    def test_manager_cannot_confirm_event(self):
        self.content.create_event('belenos','expo','Belenos expo')
        with self.assertRaises(PermissionError):
            self.service.decide_event(token=self.manager_token,tenant_id='belenos',event_id='expo',confirmed=True,now=101)

    def test_duplicate_tenant_post_denied(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.content.create_post('belenos','shared','Duplicate','promotion')

    def test_invalid_decision_denied(self):
        with self.assertRaises(ValueError):
            self.service.decide_post(token=self.owner_token,tenant_id='belenos',post_id='shared',decision='published',now=101)

if __name__=='__main__': unittest.main()
