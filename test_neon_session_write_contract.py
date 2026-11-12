"""Offline SQL parity checks for the token-authenticated draft update."""
import hashlib
import sqlite3
import unittest
from access_policy import Principal, Role
from bam_offline_gateway import BAMOfflineGateway
from neon_session_write_contract import prepare_session_priority_cas
from neon_scoped_writes import priority_cas_result


class AuthenticatedPriorityUpdateTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.app = BAMOfflineGateway(self.db, enabled=True, clock=lambda:101)
        self.owner = self.app.identities.register_password(
            email='owner@example.test', password='synthetic owner password', now=100)
        self.viewer = self.app.identities.register_password(
            email='viewer@example.test', password='synthetic viewer password', now=100)
        self.other = self.app.identities.register_password(
            email='other@example.test', password='synthetic other password', now=100)
        for identity in (self.owner,self.viewer,self.other):
            self.app.identities.set_email_verified_trusted(
                subject_id=identity, verified=True)
        self.app.directory.bootstrap_owner('shop-a',self.owner)
        self.app.directory.bootstrap_owner('shop-b',self.other)
        self.app.directory.set_member(
            Principal(self.owner,'shop-a',Role.OWNER),self.viewer,Role.VIEWER)
        self.token = self.app.sessions.issue(
            Principal(self.owner,'shop-a',Role.OWNER),now=100)
        self.viewer_token = self.app.sessions.issue(
            Principal(self.viewer,'shop-a',Role.VIEWER),now=100)
        self.rid = self.app.requests.create(
            tenant_id='shop-a',channel='facebook',
            draft_text='private alpha',suggestion='photo',
            required_items=['image'],now=101)
        self.other_rid = self.app.requests.create(
            tenant_id='shop-b',channel='facebook',
            draft_text='private bravo',suggestion='photo',
            required_items=['image'],now=101)
        self.expected = self.app.requests.get(
            tenant_id='shop-a',request_id=self.rid)['priority_token']

    def tearDown(self):
        self.db.close()

    def prepare(self,**changes):
        args=dict(raw_session_token=self.token,tenant_id='shop-a',
            request_id=self.rid,expected_priority_token=self.expected,
            priority=7,server_now=101)
        args.update(changes)
        return prepare_session_priority_cas(**args)

    def execute(self,statement):
        sql,params=statement
        self.assertEqual(sql.count('%s'),8)
        self.assertEqual(len(params),8)
        return self.db.execute(sql.replace('%s','?'),params).fetchone()

    def test_owner_can_edit_only_priority_and_cas_prevents_replay(self):
        sql,params=self.prepare()
        self.assertNotIn(self.token,sql+str(params))
        self.assertNotIn(self.owner,sql+str(params))
        self.assertEqual(params[6],hashlib.sha256(self.token.encode()).hexdigest())
        receipt=priority_cas_result(self.execute((sql,params)),
                                    expected_new_token=params[1])
        self.assertFalse(receipt['publishing_enabled'])
        self.assertEqual(receipt['posts_scheduled'],0)
        row=self.app.requests.get(tenant_id='shop-a',request_id=self.rid)
        self.assertEqual((row['priority'],row['draft_text'],row['revision']),
                         (7,'private alpha',1))
        self.assertIsNone(self.execute((sql,params)))

    def test_other_business_and_viewer_cannot_edit(self):
        self.assertIsNone(self.execute(self.prepare(
            tenant_id='shop-b',request_id=self.other_rid)))
        self.assertIsNone(self.execute(self.prepare(
            raw_session_token=self.viewer_token)))
        self.assertEqual(self.app.requests.get(
            tenant_id='shop-b',request_id=self.other_rid)['priority'],0)

    def test_live_membership_identity_expiry_and_session_revocation(self):
        self.db.execute('UPDATE members SET role=? WHERE tenant_id=? '
                        'AND subject_id=?',('viewer','shop-a',self.owner))
        self.assertIsNone(self.execute(self.prepare()))
        self.db.execute('UPDATE members SET role=? WHERE tenant_id=? '
                        'AND subject_id=?',('owner','shop-a',self.owner))
        self.db.execute('UPDATE bam_identities SET active=0 WHERE subject_id=?',
                        (self.owner,))
        self.assertIsNone(self.execute(self.prepare()))
        self.db.execute('UPDATE bam_identities SET active=1 WHERE subject_id=?',
                        (self.owner,))
        self.assertIsNone(self.execute(self.prepare(server_now=3600)))
        self.db.execute('UPDATE sessions SET revoked_at=101 WHERE token_hash=?',
                        (hashlib.sha256(self.token.encode()).hexdigest(),))
        self.assertIsNone(self.execute(self.prepare()))
        self.assertEqual(self.app.requests.get(
            tenant_id='shop-a',request_id=self.rid)['priority'],0)

    def test_invalid_context_denied_before_sql(self):
        for bad in (
            {'raw_session_token':None},
            {'raw_session_token':'short'},
            {'raw_session_token':self.token+';'},
            {'tenant_id':'shop;drop'},
            {'request_id':'bad'},
            {'expected_priority_token':'bad'},
            {'priority':11},
            {'priority':True},
            {'server_now':-1},
            {'server_now':True},
            {'server_now':2**63},
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    self.prepare(**bad)


if __name__=='__main__':
    unittest.main()
