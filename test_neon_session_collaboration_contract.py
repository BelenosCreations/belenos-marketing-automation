"""No-provider local SQL preview checks for owner-private invitations."""
import hashlib
import sqlite3
import unittest

from access_policy import Principal,Role
from bam_offline_gateway import BAMOfflineGateway
from neon_session_collaboration_contract import (
    prepare_session_pending_owner_invitations)


class SessionOwnerInvitationReadTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.app=BAMOfflineGateway(self.db,enabled=True,clock=lambda:101,
            trusted_invitation_delivery=lambda *args:None)
        self.owner=self.app.identities.register_password(
            email='owner-invite@example.test',
            password='synthetic owner password secure',now=100)
        self.other=self.app.identities.register_password(
            email='other-invite@example.test',
            password='synthetic other password secure',now=100)
        self.viewer=self.app.identities.register_password(
            email='viewer-invite@example.test',
            password='synthetic viewer password secure',now=100)
        for subject in (self.owner,self.other,self.viewer):
            self.app.identities.set_email_verified_trusted(
                subject_id=subject,verified=True)
        self.app.directory.bootstrap_owner('shop-a',self.owner)
        self.app.directory.bootstrap_owner('shop-b',self.other)
        self.app.directory.set_member(
            Principal(self.owner,'shop-a',Role.OWNER),self.viewer,Role.VIEWER)
        self.token=self.app.sessions.issue(
            Principal(self.owner,'shop-a',Role.OWNER),now=100)
        self.viewer_token=self.app.sessions.issue(
            Principal(self.viewer,'shop-a',Role.VIEWER),now=100)
        self.db.execute("""INSERT INTO bam_business_invitations
            (token_hash,tenant_id,email,role,expires_at,created_by,
             invitation_id,delivery_state)
            VALUES (?,?,?,?,?,?,?,?)""",
            ('a'*64,'shop-a','guest@private.test','viewer',500,
             self.owner,'c'*32,'delivered'))
        self.db.execute("""INSERT INTO bam_business_invitations
            (token_hash,tenant_id,email,role,expires_at,created_by,
             invitation_id,delivery_state)
            VALUES (?,?,?,?,?,?,?,?)""",
            ('b'*64,'shop-b','other@private.test','viewer',500,
             self.other,'d'*32,'delivered'))
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def read(self,**changes):
        args=dict(raw_session_token=self.token,tenant_id='shop-a',
                  server_now=101)
        args.update(changes)
        sql,params=prepare_session_pending_owner_invitations(**args)
        self.assertEqual(sql.count('%s'),len(params))
        self.assertEqual(len(params),4)
        self.assertNotIn(self.token,sql+str(params))
        self.assertNotIn(self.owner,sql+str(params))
        self.assertNotIn('v.token_hash',sql)
        return self.db.execute(sql.replace('%s','?'),params).fetchall()

    def test_only_current_owner_reads_own_delivered_pending_metadata(self):
        rows=self.read()
        self.assertEqual(rows,[('c'*32,'guest@private.test','viewer',500)])
        self.assertEqual(self.read(tenant_id='shop-b'),[])
        self.assertEqual(self.read(raw_session_token=self.viewer_token),[])

    def test_expired_consumed_revoked_invites_hidden(self):
        self.assertEqual(self.read(server_now=500),[])
        self.db.execute("""UPDATE bam_business_invitations
            SET consumed_at=102 WHERE tenant_id='shop-a'""")
        self.assertEqual(self.read(),[])
        self.db.execute("""UPDATE bam_business_invitations
            SET consumed_at=NULL,revoked_at=102 WHERE tenant_id='shop-a'""")
        self.assertEqual(self.read(),[])
        self.db.execute("""UPDATE bam_business_invitations
            SET revoked_at=NULL,delivery_state='failed'
            WHERE tenant_id='shop-a'""")
        self.assertEqual(self.read(),[])

    def test_old_owner_token_fails_on_role_change_or_revocation(self):
        self.db.execute("""UPDATE members SET role='viewer'
            WHERE tenant_id='shop-a' AND subject_id=?""",(self.owner,))
        self.assertEqual(self.read(),[])
        self.db.execute("""UPDATE members SET role='owner'
            WHERE tenant_id='shop-a' AND subject_id=?""",(self.owner,))
        self.db.execute("""UPDATE bam_identities SET email_verified=0
            WHERE subject_id=?""",(self.owner,))
        self.assertEqual(self.read(),[])
        self.db.execute("""UPDATE bam_identities SET email_verified=1
            WHERE subject_id=?""",(self.owner,))
        self.assertEqual(self.read(server_now=3700),[])
        self.db.execute("""UPDATE sessions SET revoked_at=104
            WHERE token_hash=?""",
            (hashlib.sha256(self.token.encode()).hexdigest(),))
        self.assertEqual(self.read(),[])

    def test_invalid_session_context_rejected(self):
        for change in (
            {'raw_session_token':None},
            {'raw_session_token':'short'},
            {'raw_session_token':self.token+';'},
            {'tenant_id':'shop a'},
            {'tenant_id':'shop;drop'},
            {'server_now':True},
            {'server_now':-1},
            {'server_now':2**63},
        ):
            with self.subTest(change=change):
                args=dict(raw_session_token=self.token,tenant_id='shop-a',
                          server_now=101)
                args.update(change)
                with self.assertRaises(ValueError):
                    prepare_session_pending_owner_invitations(**args)


if __name__=='__main__':
    unittest.main()
