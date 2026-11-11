import sqlite3
import unittest
from datetime import datetime, timezone
from access_policy import Principal, Role
from accounts import AccountDirectory
from sessions import SessionStore
from engine import initialize, stage
from workflow import setup, upsert_discovery
from approval_gateway import ApprovalGateway

class ApprovalGatewayTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        initialize(self.db); setup(self.db)
        self.directory=AccountDirectory(self.db)
        self.directory.bootstrap_owner('belenos','owner')
        self.owner=Principal('owner','belenos',Role.OWNER)
        self.directory.set_member(self.owner,'manager',Role.MARKETING_MANAGER)
        self.sessions=SessionStore(self.db)
        self.gateway=ApprovalGateway(self.sessions,self.directory,self.db)
        self.at=datetime(2026,11,10,15,tzinfo=timezone.utc)
        self.owner_token=self.sessions.issue(self.owner,now=int(self.at.timestamp()))
        self.manager_token=self.sessions.issue(Principal('manager','belenos',Role.MARKETING_MANAGER),now=int(self.at.timestamp()))
        self.promo=stage(self.db,slot='A',content='New product',category='promotion',now=self.at)[0]
        self.community=stage(self.db,slot='B',content='Favorite print?',category='community',now=self.at)[0]
        self.gateway.ownership.register(kind='post',resource_id=self.promo,tenant_id='belenos')
        self.gateway.ownership.register(kind='post',resource_id=self.community,tenant_id='belenos')

    def test_owner_approves_promotion(self):
        self.gateway.decide_post(token=self.owner_token,tenant_id='belenos',post_id=self.promo,decision='approved',at=self.at)
        self.assertEqual(self.db.execute('SELECT decision,actor FROM approvals WHERE post_id=?',(self.promo,)).fetchone(),('approved','owner'))

    def test_manager_cannot_approve_promotion(self):
        with self.assertRaises(PermissionError):
            self.gateway.decide_post(token=self.manager_token,tenant_id='belenos',post_id=self.promo,decision='approved',at=self.at)

    def test_manager_can_approve_routine(self):
        self.gateway.decide_post(token=self.manager_token,tenant_id='belenos',post_id=self.community,decision='approved',at=self.at)

    def test_manager_cannot_revoke(self):
        with self.assertRaises(PermissionError):
            self.gateway.decide_post(token=self.manager_token,tenant_id='belenos',post_id=self.community,decision='revoked',at=self.at)

    def test_new_owner_role_requires_a_fresh_session(self):
        self.directory.set_member(self.owner,'manager',Role.OWNER)
        with self.assertRaises(PermissionError):
            self.gateway.decide_post(token=self.manager_token,
                tenant_id='belenos',post_id=self.promo,
                decision='approved',at=self.at)
        # An explicitly issued current-role session has the new permissions.
        fresh=self.sessions.issue(
            Principal('manager','belenos',Role.OWNER),
            now=int(self.at.timestamp()))
        self.gateway.decide_post(token=fresh,
            tenant_id='belenos',post_id=self.promo,
            decision='approved',at=self.at)

    def test_role_downgrade_immediate(self):
        self.directory.set_member(self.owner,'manager',Role.VIEWER)
        with self.assertRaises(PermissionError):
            self.gateway.decide_post(token=self.manager_token,tenant_id='belenos',post_id=self.community,decision='approved',at=self.at)

    def test_inactive_immediate(self):
        self.directory.set_member(self.owner,'manager',Role.MARKETING_MANAGER,active=False)
        with self.assertRaises(PermissionError):
            self.gateway.decide_post(token=self.manager_token,tenant_id='belenos',post_id=self.community,decision='approved',at=self.at)

    def test_cross_tenant_denied(self):
        with self.assertRaises(PermissionError):
            self.gateway.decide_post(token=self.owner_token,tenant_id='other',post_id=self.promo,decision='approved',at=self.at)

    def test_expired_session_denied(self):
        later=datetime(2026,11,10,17,tzinfo=timezone.utc)
        with self.assertRaises(PermissionError):
            self.gateway.decide_post(token=self.owner_token,tenant_id='belenos',post_id=self.promo,decision='approved',at=later)

    def test_revoked_session_denied(self):
        self.sessions.revoke(self.owner_token,now=int(self.at.timestamp()))
        with self.assertRaises(PermissionError):
            self.gateway.decide_post(token=self.owner_token,tenant_id='belenos',post_id=self.promo,decision='approved',at=self.at)

    def test_event_confirmation_owner_only(self):
        e=upsert_discovery(self.db,title='Fair',event_start=self.at,source_url='https://example.com/fair',participation='unknown',at=self.at)
        self.gateway.ownership.register(kind='event',resource_id=e,tenant_id='belenos')
        with self.assertRaises(PermissionError):
            self.gateway.decide_event(token=self.manager_token,tenant_id='belenos',event_id=e,confirmed=True,at=self.at)
        self.gateway.decide_event(token=self.owner_token,tenant_id='belenos',event_id=e,confirmed=True,at=self.at)
        self.assertEqual(self.db.execute('SELECT state FROM discovered_events WHERE id=?',(e,)).fetchone()[0],'confirmed')

    def test_blocked_post_cannot_be_approved(self):
        blocked=stage(self.db,slot='C',content='50% off',category='invented_offer',now=self.at)[0]
        self.gateway.ownership.register(kind='post',resource_id=blocked,tenant_id='belenos')
        with self.assertRaises(ValueError):
            self.gateway.decide_post(token=self.owner_token,tenant_id='belenos',post_id=blocked,decision='approved',at=self.at)

    def test_invalid_token_denied(self):
        with self.assertRaises(PermissionError):
            self.gateway.decide_post(token='fake',tenant_id='belenos',post_id=self.promo,decision='approved',at=self.at)

    def test_unowned_post_denied(self):
        post=stage(self.db,slot='D',content='New item',category='promotion',now=self.at)[0]
        with self.assertRaises(PermissionError):
            self.gateway.decide_post(token=self.owner_token,tenant_id='belenos',post_id=post,decision='approved',at=self.at)

    def test_foreign_owned_post_denied(self):
        post=stage(self.db,slot='E',content='Another item',category='promotion',now=self.at)[0]
        self.gateway.ownership.register(kind='post',resource_id=post,tenant_id='other')
        with self.assertRaises(PermissionError):
            self.gateway.decide_post(token=self.owner_token,tenant_id='belenos',post_id=post,decision='approved',at=self.at)

    def test_ownership_cannot_be_reassigned(self):
        with self.assertRaises(PermissionError):
            self.gateway.ownership.register(kind='post',resource_id=self.promo,tenant_id='other')

    def test_unowned_event_denied(self):
        e=upsert_discovery(self.db,title='Expo',event_start=self.at,source_url='https://example.com/expo',participation='unknown',at=self.at)
        with self.assertRaises(PermissionError):
            self.gateway.decide_event(token=self.owner_token,tenant_id='belenos',event_id=e,confirmed=True,at=self.at)

if __name__=='__main__': unittest.main()
