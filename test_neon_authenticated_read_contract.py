"""Security contract tests without connecting to external services."""
import hashlib
import sqlite3
import unittest
from access_policy import Principal,Role
from bam_offline_gateway import BAMOfflineGateway
from neon_authenticated_read_contract import (
    prepare_session_draft_read,prepare_session_calendar_read)


class SessionScopedQueryTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.gateway=BAMOfflineGateway(self.db,enabled=True,clock=lambda:101)
        self.actor=self.gateway.identities.register_password(
            email='session-fixture@example.test',
            password='correct synthetic password phrase',now=100)
        self.gateway.identities.set_email_verified_trusted(
            subject_id=self.actor,verified=True)
        self.gateway.directory.bootstrap_owner('shop-fixture',self.actor)
        self.token=self.gateway.sessions.issue(Principal(
            self.actor,'shop-fixture',Role.OWNER),now=100)
        self.rid=self.gateway.requests.create(
            tenant_id='shop-fixture',channel='facebook',
            draft_text='private draft',suggestion='photo',
            required_items=['image'],now=101)

    def tearDown(self):
        self.db.close()

    def _query(self,statement):
        sql,params=statement
        self.assertEqual(sql.count('%s'),len(params))
        return self.db.execute(sql.replace('%s','?'),params).fetchone()

    def _draft(self,**overrides):
        args=dict(raw_session_token=self.token,tenant_id='shop-fixture',
                  request_id=self.rid,server_now=101)
        args.update(overrides)
        return prepare_session_draft_read(**args)

    def test_raw_session_bearer_never_reaches_sql_or_query_parameters(self):
        sql,params=self._draft()
        self.assertNotIn(self.token,sql)
        self.assertNotIn(self.token,str(params))
        self.assertEqual(params[0],
                         hashlib.sha256(self.token.encode()).hexdigest())
        self.assertEqual(self._query((sql,params))[2],'private draft')

    def test_current_permissions_and_revocation_checked_in_one_sql(self):
        self.assertIsNone(self._query(self._draft(tenant_id='other')))
        self.assertIsNone(self._query(self._draft(server_now=3700)))
        self.db.execute('UPDATE members SET role=? WHERE tenant_id=? '
            'AND subject_id=?',('viewer','shop-fixture',self.actor))
        self.assertIsNone(self._query(self._draft()))
        self.db.execute('UPDATE members SET role=? WHERE tenant_id=? '
            'AND subject_id=?',('owner','shop-fixture',self.actor))
        self.db.execute('UPDATE bam_identities SET email_verified=0 '
            'WHERE subject_id=?',(self.actor,))
        self.assertIsNone(self._query(self._draft()))
        self.db.execute('UPDATE bam_identities SET email_verified=1 '
            'WHERE subject_id=?',(self.actor,))
        self.db.execute('UPDATE sessions SET revoked_at=101 '
            'WHERE token_hash=?',(
              hashlib.sha256(self.token.encode()).hexdigest(),))
        self.assertIsNone(self._query(self._draft()))

    def test_calendar_is_nonpublishing_and_uses_same_active_session(self):
        sql,params=prepare_session_calendar_read(
            raw_session_token=self.token,tenant_id='shop-fixture',
            request_id=self.rid,server_now=101)
        self.assertNotIn(self.token,str(params))
        self.assertIsNone(self._query((sql,params)))
        self.assertIn('s.revoked_at IS NULL',sql)
        self.assertIn('m.role=s.role',sql)

    def test_malformed_context_denied_before_building_sql(self):
        for change in (
            {'raw_session_token':None},
            {'raw_session_token':'short'},
            {'raw_session_token':'t'*42+';'},
            {'tenant_id':'shop;drop'},
            {'request_id':'invalid'},
            {'server_now':True},
            {'server_now':-1}
        ):
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    self._draft(**change)


if __name__=='__main__':
    unittest.main()
