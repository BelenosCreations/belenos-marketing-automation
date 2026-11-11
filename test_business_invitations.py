import sqlite3
import unittest
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from identity_auth import IdentityAuth
from business_invitations import BusinessInvitations

class InvitationTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.directory=AccountDirectory(self.db)
        self.sessions=SessionStore(self.db)
        self.auth=IdentityAuth(self.db,self.sessions,self.directory)
        self.owner=self.auth.register_password(email='owner@example.com',
            password='owner password phrase 123',now=100)
        self.guest=self.auth.register_password(email='guest@example.com',
            password='guest password phrase 123',now=100)
        self.auth.set_email_verified_trusted(subject_id=self.owner,verified=True)
        self.auth.set_email_verified_trusted(subject_id=self.guest,verified=True)
        self.directory.bootstrap_owner('shop',self.owner)
        self.directory.bootstrap_owner('other','another_owner')
        self.owner_token=self.auth.login_password(email='owner@example.com',
            password='owner password phrase 123',tenant_id='shop',now=101)
        self.outbox=[]
        self.invites=BusinessInvitations(db=self.db,sessions=self.sessions,
            directory=self.directory,auth=self.auth,
            deliver=lambda email,tenant,token:self.outbox.append((email,tenant,token)))

    def invite(self,**overrides):
        params=dict(owner_session=self.owner_token,tenant_id='shop',
            email='guest@example.com',role=Role.CONTENT_CREATOR,now=102)
        params.update(overrides)
        return self.invites.invite(**params)

    def test_invite_and_accept(self):
        self.invite()
        token=self.outbox[-1][2]
        result=self.invites.accept_trusted(verified_subject_id=self.guest,
            token=token,now=103)
        self.assertEqual(result['role'],'content_creator')
        self.assertEqual(self.directory.resolve('shop',self.guest).role,
                         Role.CONTENT_CREATOR)
        with self.assertRaises(PermissionError):
            self.invites.accept_trusted(verified_subject_id=self.guest,
                token=token,now=104)

    def test_invitation_cannot_grant_owner(self):
        with self.assertRaises(PermissionError):
            self.invite(role=Role.OWNER)

    def test_cross_tenant_invite_denied(self):
        with self.assertRaises(PermissionError):
            self.invite(tenant_id='other')

    def test_wrong_identity_denied(self):
        self.invite()
        with self.assertRaises(PermissionError):
            self.invites.accept_trusted(verified_subject_id=self.owner,
                token=self.outbox[-1][2],now=103)

    def test_expired_invitation_denied(self):
        self.invite()
        with self.assertRaises(PermissionError):
            self.invites.accept_trusted(verified_subject_id=self.guest,
                token=self.outbox[-1][2],now=604903)

    def test_no_invitation_token_plaintext_in_db(self):
        self.invite()
        token=self.outbox[-1][2]
        stored=self.db.execute(
            'SELECT token_hash FROM bam_business_invitations').fetchone()[0]
        self.assertNotEqual(stored,token)

if __name__=='__main__':unittest.main()
