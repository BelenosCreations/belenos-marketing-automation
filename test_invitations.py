import sqlite3
import unittest
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from invitations import InvitationService

class InvitationTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.directory=AccountDirectory(self.db)
        self.directory.bootstrap_owner('belenos','owner')
        self.directory.bootstrap_owner('other','other_owner')
        self.sessions=SessionStore(self.db)
        self.owner_token=self.sessions.issue(Principal('owner','belenos',Role.OWNER),now=100)
        self.other_token=self.sessions.issue(Principal('other_owner','other',Role.OWNER),now=100)
        self.directory.set_member(Principal('owner','belenos',Role.OWNER),'manager',Role.MARKETING_MANAGER)
        self.manager_token=self.sessions.issue(Principal('manager','belenos',Role.MARKETING_MANAGER),now=100)
        self.service=InvitationService(self.db,self.directory,self.sessions)

    def invite(self):
        return self.service.create(actor_token=self.owner_token,tenant_id='belenos',role=Role.CONTENT_CREATOR,now=101)

    def test_owner_creates_and_redeems(self):
        token=self.invite()
        self.service.redeem(token=token,tenant_id='belenos',verified_subject_id='new',now=102)
        self.assertEqual(self.directory.resolve('belenos','new').role,Role.CONTENT_CREATOR)

    def test_token_not_stored_plaintext(self):
        token=self.invite()
        self.assertNotEqual(self.db.execute('SELECT token_hash FROM invitations').fetchone()[0],token)

    def test_replay_denied(self):
        token=self.invite()
        self.service.redeem(token=token,tenant_id='belenos',verified_subject_id='new',now=102)
        with self.assertRaises(PermissionError):
            self.service.redeem(token=token,tenant_id='belenos',verified_subject_id='other_new',now=103)

    def test_cross_tenant_denied(self):
        token=self.invite()
        with self.assertRaises(PermissionError):
            self.service.redeem(token=token,tenant_id='other',verified_subject_id='new',now=102)

    def test_expired_denied(self):
        token=self.invite()
        with self.assertRaises(PermissionError):
            self.service.redeem(token=token,tenant_id='belenos',verified_subject_id='new',now=86500)

    def test_manager_cannot_invite(self):
        with self.assertRaises(PermissionError):
            self.service.create(actor_token=self.manager_token,tenant_id='belenos',role=Role.VIEWER,now=101)

    def test_owner_role_invitation_denied(self):
        with self.assertRaises(PermissionError):
            self.service.create(actor_token=self.owner_token,tenant_id='belenos',role=Role.OWNER,now=101)

    def test_revoked_denied(self):
        token=self.invite()
        self.service.revoke(actor_token=self.owner_token,tenant_id='belenos',invite_token=token,now=102)
        with self.assertRaises(PermissionError):
            self.service.redeem(token=token,tenant_id='belenos',verified_subject_id='new',now=103)

    def test_manager_cannot_revoke(self):
        token=self.invite()
        with self.assertRaises(PermissionError):
            self.service.revoke(actor_token=self.manager_token,tenant_id='belenos',invite_token=token,now=102)

    def test_existing_member_cannot_redeem(self):
        token=self.invite()
        with self.assertRaises(PermissionError):
            self.service.redeem(token=token,tenant_id='belenos',verified_subject_id='manager',now=102)

    def test_invalid_ttl(self):
        with self.assertRaises(ValueError):
            self.service.create(actor_token=self.owner_token,tenant_id='belenos',role=Role.VIEWER,ttl_seconds=0,now=101)

    def test_cross_tenant_owner_cannot_issue(self):
        with self.assertRaises(PermissionError):
            self.service.create(actor_token=self.other_token,tenant_id='belenos',role=Role.VIEWER,now=101)

if __name__=='__main__': unittest.main()
