"""Simulated PostgreSQL CAS SQL verified on local SQLite fixtures only.

The tests translate DB-API placeholders solely for syntax/behavior checks.
They do not establish compatibility with real Neon, nor allow hosted edits.
"""
import sqlite3
import unittest
from access_policy import Principal,Role
from bam_offline_gateway import BAMOfflineGateway
from neon_scoped_writes import prepare_draft_priority_cas,priority_cas_result


class NeonScopedCASWriteTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.app=BAMOfflineGateway(self.db,enabled=True,clock=lambda:101)
        self.a=self.app.identities.register_password(
            email='write-a@example.test',
            password='correct alpha test password',now=100)
        self.b=self.app.identities.register_password(
            email='write-b@example.test',
            password='correct bravo test password',now=100)
        self.viewer=self.app.identities.register_password(
            email='write-viewer@example.test',
            password='correct viewer test password',now=100)
        self.editor=self.app.identities.register_password(
            email='write-editor@example.test',
            password='correct editor test password',now=100)
        for identity in (self.a,self.b,self.viewer,self.editor):
            self.app.identities.set_email_verified_trusted(
                subject_id=identity,verified=True)
        self.app.directory.bootstrap_owner('first',self.a)
        self.app.directory.bootstrap_owner('second',self.b)
        actor=Principal(self.a,'first',Role.OWNER)
        self.app.directory.set_member(actor,self.viewer,Role.VIEWER)
        self.app.directory.set_member(actor,self.editor,Role.CONTENT_CREATOR)
        self.rid=self.app.requests.create(
            tenant_id='first',channel='facebook',
            draft_text='Private first content',suggestion='image',
            required_items=['image'],now=100)
        self.rid_b=self.app.requests.create(
            tenant_id='second',channel='facebook',
            draft_text='Private second content',suggestion='image',
            required_items=['image'],now=100)
    def tearDown(self):
        self.db.close()

    def prepare(self,*,actor=None,tenant='first',request=None,token=None,
                priority=5):
        draft=self.app.requests.get(
            tenant_id='first',request_id=self.rid)
        return prepare_draft_priority_cas(
            tenant_id=tenant,
            request_id=self.rid if request is None else request,
            verified_subject_id=self.a if actor is None else actor,
            expected_priority_token=(draft['priority_token'] if token is None
                else token),priority=priority,server_now=101)

    def run_query(self,statement):
        sql,params=statement
        self.assertEqual(sql.count('%s'),len(params))
        self.assertEqual(len(params),7)
        self.assertNotIn('first',sql)
        self.assertNotIn(self.a,sql)
        # Query contract is PostgreSQL-style; only test-only local conversion.
        return self.db.execute(sql.replace('%s','?'),params).fetchone()

    def test_owner_can_change_priority_without_changing_copy_or_revision(self):
        sql,params=self.prepare(priority=8)
        result=priority_cas_result(self.run_query((sql,params)),
            expected_new_token=params[1])
        after=self.app.requests.get(tenant_id='first',request_id=self.rid)
        self.assertEqual(after['priority'],8)
        self.assertEqual(after['revision'],1)
        self.assertEqual(after['draft_text'],'Private first content')
        self.assertEqual(result['draft_revision'],1)
        self.assertFalse(result['publishing_enabled'])
        self.assertEqual(result['posts_scheduled'],0)

    def test_stale_cas_token_cannot_overwrite(self):
        first=self.prepare(priority=8)
        second=self.prepare(priority=-3)
        self.assertIsNotNone(self.run_query(first))
        self.assertIsNone(self.run_query(second))
        with self.assertRaises(PermissionError):
            priority_cas_result(None,expected_new_token=second[1][1])
        self.assertEqual(self.app.requests.get(
            tenant_id='first',request_id=self.rid)['priority'],8)

    def test_cross_tenant_and_viewer_are_denied_at_statement_time(self):
        for change in (
            dict(actor=self.b),
            dict(actor=self.viewer),
            dict(tenant='second'),
            dict(request=self.rid_b)):
            with self.subTest(change=change):
                self.assertIsNone(self.run_query(self.prepare(**change)))
        self.assertEqual(self.app.requests.get(
            tenant_id='second',request_id=self.rid_b)['priority'],0)
        self.assertEqual(self.app.requests.get(
            tenant_id='first',request_id=self.rid)['priority'],0)

    def test_editor_current_membership_and_revocation(self):
        self.assertIsNotNone(self.run_query(
            self.prepare(actor=self.editor,priority=3)))
        draft=self.app.requests.get(tenant_id='first',request_id=self.rid)
        current=draft['priority_token']
        valid=self.prepare(actor=self.editor,token=current,priority=4)
        self.db.execute('UPDATE members SET active=0 WHERE tenant_id=? '
            'AND subject_id=?',('first',self.editor))
        self.assertIsNone(self.run_query(valid))
        self.db.execute('UPDATE members SET active=1 WHERE tenant_id=? '
            'AND subject_id=?',('first',self.editor))
        self.db.execute('UPDATE bam_identities SET active=0 '
            'WHERE subject_id=?',(self.editor,))
        self.assertIsNone(self.run_query(valid))

    def test_invalid_inputs_and_receipts_rejected(self):
        for changes in (
            {'priority':11},{'priority':True},{'priority':-11},
            {'token':'bad'},{'actor':'not a subject!'},{'tenant':'a; DROP'},
            {'request':'abc'}):
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    self.prepare(**changes)
        with self.assertRaises(ValueError):
            priority_cas_result((5,'invalid',1),
                expected_new_token='f'*32)


if __name__=='__main__':
    unittest.main()
