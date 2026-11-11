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

    def test_invitation_audit_tracks_accepted_link_without_secrets(self):
        created=self.invite()
        link=self.outbox[-1][2]
        before=self.invites.history_current(
            owner_session=self.owner_token,now=103)
        self.assertEqual(before['status'],'private_invitation_activity')
        self.assertEqual([e['action'] for e in before['events']],
                         ['delivered'])
        self.assertEqual(before['events'][0]['invitation_id'],
                         created['invitation_id'])
        self.invites.accept_trusted(
            verified_subject_id=self.guest,token=link,now=104)
        after=self.invites.history_current(
            owner_session=self.owner_token,now=105)
        self.assertEqual([e['action'] for e in after['events']],
                         ['accepted','delivered'])
        self.assertNotIn(link,str(after))
        self.assertNotIn('guest@example.com',str(after))
        self.assertNotIn('token_hash',str(after))
        # Reopen offline storage without generating fictional history.
        another=BusinessInvitations(db=self.db,sessions=self.sessions,
            directory=self.directory,auth=self.auth,
            deliver=lambda *args:None)
        self.assertEqual(another.history_current(
            owner_session=self.owner_token,now=105),after)

    def test_invitation_cancel_and_delivery_failure_are_audited(self):
        created=self.invite()
        self.invites.cancel_current(
            owner_session=self.owner_token,
            invitation_id=created['invitation_id'],now=103)
        def fail(*args):
            raise OSError('offline simulated delivery failure')
        self.invites.deliver=fail
        with self.assertRaises(RuntimeError):
            self.invite(now=104)
        history=self.invites.history_current(
            owner_session=self.owner_token,now=105)
        self.assertEqual([e['action'] for e in history['events']],
                         ['delivery_failed','cancelled','delivered'])
        self.assertTrue(all(e['occurred_at'] in (102,103,104)
                            for e in history['events']))

    def test_invitation_audit_owner_scoped_and_limited(self):
        self.invite()
        other=self.sessions.issue(
            Principal('another_owner','other',Role.OWNER),now=100)
        self.assertEqual(self.invites.history_current(
            owner_session=other,now=103)['events'],[])
        viewer=self.sessions.issue(
            Principal('viewer','shop',Role.VIEWER),now=100)
        with self.assertRaises(PermissionError):
            self.invites.history_current(owner_session=viewer,now=103)
        for limit in (0,31,True,'10'):
            with self.assertRaises(ValueError):
                self.invites.history_current(owner_session=self.owner_token,
                    now=103,limit=limit)
        owner=self.invites.history_current(
            owner_session=self.owner_token,now=103,limit=1)
        self.assertEqual(len(owner['events']),1)

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

    def test_repeat_active_invitation_is_refused_without_second_delivery(self):
        first=self.invite()
        with self.assertRaises(ValueError):
            self.invite(role=Role.VIEWER,now=103)
        self.assertEqual(len(self.outbox),1)
        pending=self.invites.pending_current(
            owner_session=self.owner_token,now=104)
        self.assertEqual([x['invitation_id'] for x in pending['items']],
                         [first['invitation_id']])

    def test_cancel_then_reinvite_creates_new_single_use_link(self):
        first=self.invite()
        self.invites.cancel_current(owner_session=self.owner_token,
            invitation_id=first['invitation_id'],now=103)
        replacement=self.invite(now=104)
        self.assertNotEqual(first['invitation_id'],
                            replacement['invitation_id'])
        self.assertEqual(len(self.outbox),2)
        pending=self.invites.pending_current(
            owner_session=self.owner_token,now=105)
        self.assertEqual([x['invitation_id'] for x in pending['items']],
                         [replacement['invitation_id']])

    def test_expired_or_failed_invitation_does_not_block_reinvite(self):
        first=self.invite()
        # Seven days later requires a newly authenticated owner session.
        fresh=self.sessions.issue(
            Principal(self.owner,'shop',Role.OWNER),now=604900)
        later=self.invite(owner_session=fresh,now=604903)
        self.assertNotEqual(later['invitation_id'],first['invitation_id'])
        self.assertEqual(len(self.outbox),2)
        # A failed trusted delivery must never reserve the recipient email.
        def broken(*args):
            raise OSError('offline test delivery failure')
        self.invites.deliver=broken
        self.invites.cancel_current(owner_session=fresh,
            invitation_id=later['invitation_id'],now=604904)
        with self.assertRaises(RuntimeError):
            self.invite(owner_session=fresh,now=604905)
        self.invites.deliver=lambda email,tenant,token:self.outbox.append(
            (email,tenant,token))
        self.assertTrue(self.invite(owner_session=fresh,now=604906)
                        ['invitation_created'])

    def test_existing_active_or_inactive_member_cannot_be_reinvited(self):
        self.invite()
        self.invites.accept_trusted(verified_subject_id=self.guest,
            token=self.outbox[-1][2],now=103)
        with self.assertRaises(ValueError):
            self.invite(now=104)
        self.directory.set_member(
            Principal(self.owner,'shop',Role.OWNER),
            self.guest,Role.CONTENT_CREATOR,active=False)
        with self.assertRaises(ValueError):
            self.invite(now=105)
        self.assertEqual(len(self.outbox),1)

    def test_other_business_can_invite_same_email_independently(self):
        self.invite()
        other_owner=self.sessions.issue(
            Principal('another_owner','other',Role.OWNER),now=100)
        second=self.invites.invite(owner_session=other_owner,
            tenant_id='other',email='guest@example.com',
            role=Role.VIEWER,now=102)
        self.assertTrue(second['invitation_created'])
        self.assertEqual(len(self.outbox),2)
        self.assertEqual(len(self.invites.pending_current(
            owner_session=self.owner_token,now=103)['items']),1)
        self.assertEqual(len(self.invites.pending_current(
            owner_session=other_owner,now=103)['items']),1)

    def test_owner_pending_list_and_single_use_cancellation(self):
        created=self.invite()
        invitation_id=created['invitation_id']
        self.assertEqual(len(invitation_id),32)
        pending=self.invites.pending_current(
            owner_session=self.owner_token,now=103)
        self.assertEqual(pending['tenant_id'],'shop')
        self.assertEqual(len(pending['items']),1)
        self.assertEqual(pending['items'][0]['invitation_id'],invitation_id)
        self.assertEqual(pending['items'][0]['email'],'guest@example.com')
        self.assertNotIn(self.outbox[-1][2],str(pending))
        self.assertNotIn('token_hash',str(pending))
        cancelled=self.invites.cancel_current(
            owner_session=self.owner_token,
            invitation_id=invitation_id,now=104)
        self.assertEqual(cancelled['status'],'cancelled')
        self.assertEqual(self.invites.pending_current(
            owner_session=self.owner_token,now=105)['items'],[])
        with self.assertRaises(KeyError):
            self.invites.cancel_current(owner_session=self.owner_token,
                invitation_id=invitation_id,now=105)
        with self.assertRaises(PermissionError):
            self.invites.accept_trusted(verified_subject_id=self.guest,
                token=self.outbox[-1][2],now=105)

    def test_nonowner_and_other_business_denied_for_pending_preview(self):
        guest_token=self.sessions.issue(
            Principal(self.guest,'shop',Role.VIEWER),now=100)
        self.invite()
        with self.assertRaises(PermissionError):
            self.invites.pending_current(owner_session=guest_token,now=102)
        with self.assertRaises(PermissionError):
            self.invites.cancel_current(owner_session=guest_token,
                invitation_id=self.invites.pending_current(
                    owner_session=self.owner_token,now=103)['items'][0]
                    ['invitation_id'],now=103)
        self.assertEqual(self.invites.pending_current(
            owner_session=self.owner_token,now=103)['items'][0]['role'],
            'content_creator')

    def test_undelivered_invitation_cannot_be_redeemed(self):
        holder={}
        def deliver(email,tenant,token):
            holder['token']=token
            with self.assertRaises(PermissionError):
                self.invites.accept_trusted(
                    verified_subject_id=self.guest,token=token,now=103)
        self.invites.deliver=deliver
        result=self.invite()
        self.assertTrue(result['invitation_created'])
        success=self.invites.accept_trusted(
            verified_subject_id=self.guest,token=holder['token'],now=104)
        self.assertTrue(success['membership_created'])

    def test_delivery_failure_revokes_token_and_hides_pending(self):
        received={}
        def fail(email,tenant,token):
            received['token']=token
            raise OSError('Simulated transport failure')
        self.invites.deliver=fail
        with self.assertRaises(RuntimeError):
            self.invite()
        self.assertEqual(self.invites.pending_current(
            owner_session=self.owner_token,now=104)['items'],[])
        with self.assertRaises(PermissionError):
            self.invites.accept_trusted(
                verified_subject_id=self.guest,token=received['token'],now=104)

    def test_legacy_invitation_schema_migration(self):
        legacy=sqlite3.connect(':memory:')
        try:
            legacy.execute("""CREATE TABLE bam_business_invitations (
                token_hash TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,
                email TEXT NOT NULL,role TEXT NOT NULL,
                expires_at INTEGER NOT NULL,consumed_at INTEGER,
                created_by TEXT NOT NULL)""")
            legacy.execute("""INSERT INTO bam_business_invitations
                VALUES ('a','shop','guest@example.com','viewer',500,NULL,'boss')""")
            legacy.commit()
            first=BusinessInvitations(
                db=legacy,sessions=self.sessions,directory=self.directory,
                auth=self.auth,deliver=lambda *args:None)
            identifier=legacy.execute(
                'SELECT invitation_id FROM bam_business_invitations').fetchone()[0]
            self.assertEqual(len(identifier),32)
            self.assertEqual(legacy.execute(
                'SELECT delivery_state FROM bam_business_invitations'
                ).fetchone()[0],'delivered')
            second=BusinessInvitations(
                db=legacy,sessions=self.sessions,directory=self.directory,
                auth=self.auth,deliver=lambda *args:None)
            self.assertEqual(legacy.execute(
                'SELECT invitation_id FROM bam_business_invitations'
                ).fetchone()[0],identifier)
            self.assertIsNotNone(second)
            self.assertIsNotNone(first)
        finally:
            legacy.close()

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
