"""Exercise prepared PostgreSQL-style query shape against local SQLite.

This compatibility simulation translates placeholders for offline testing.
It is NOT a PostgreSQL driver or live Neon security proof.
"""
import sqlite3
import unittest
from bam_offline_gateway import BAMOfflineGateway
from neon_scoped_queries import (
    draft_select_for_verified_member,calendar_select_for_verified_member,
    summarize_held_draft_row,summarize_calendar_row)


class NeonPreparedReadTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.app=BAMOfflineGateway(self.db,enabled=True,clock=lambda:101)
        self.owner_a=self.app.identities.register_password(
            email='owner-a@example.test',password='correct horse battery alpha',
            now=100)
        self.owner_b=self.app.identities.register_password(
            email='owner-b@example.test',password='correct horse battery bravo',
            now=100)
        for subject in (self.owner_a,self.owner_b):
            self.app.identities.set_email_verified_trusted(
                subject_id=subject,verified=True)
        self.app.directory.bootstrap_owner('shop-a',self.owner_a)
        self.app.directory.bootstrap_owner('shop-b',self.owner_b)
        self.rid_a=self.app.requests.create(tenant_id='shop-a',
            channel='facebook',draft_text='private alpha copy',
            suggestion='photo',required_items=['image'],now=100)
        self.rid_b=self.app.requests.create(tenant_id='shop-b',
            channel='facebook',draft_text='private beta copy',
            suggestion='photo',required_items=['image'],now=100)
    def tearDown(self):
        self.db.close()

    def query(self,statement):
        sql,params=statement
        self.assertEqual(sql.count('%s'),len(params))
        self.assertNotIn('shop-a',sql)
        self.assertNotIn('shop-b',sql)
        self.assertNotIn(self.owner_a,sql)
        self.assertNotIn(self.owner_b,sql)
        # The syntax is parameterized PostgreSQL DB-API, adapted to SQLite
        # solely for offline query-shape testing.
        return self.db.execute(sql.replace('%s','?'),params).fetchone()

    def test_draft_is_join_scoped_to_current_verified_membership(self):
        read=lambda tenant,rid,user:self.query(
            draft_select_for_verified_member(tenant_id=tenant,
                request_id=rid,verified_subject_id=user))
        a=summarize_held_draft_row(read('shop-a',self.rid_a,self.owner_a))
        b=summarize_held_draft_row(read('shop-b',self.rid_b,self.owner_b))
        self.assertEqual(a['draft_text'],'private alpha copy')
        self.assertEqual(b['draft_text'],'private beta copy')
        self.assertFalse(a['publishing_enabled'])
        self.assertEqual(a['posts_scheduled'],0)
        self.assertIsNone(read('shop-b',self.rid_b,self.owner_a))
        self.assertIsNone(read('shop-a',self.rid_a,self.owner_b))
        self.assertIsNone(read('shop-b',self.rid_a,self.owner_b))
        self.db.execute('UPDATE members SET active=0 '
            'WHERE tenant_id=? AND subject_id=?',('shop-a',self.owner_a))
        self.assertIsNone(read('shop-a',self.rid_a,self.owner_a))
        self.db.execute('UPDATE members SET active=1 WHERE tenant_id=? '
            'AND subject_id=?',('shop-a',self.owner_a))
        self.db.execute('UPDATE bam_identities SET active=0 '
            'WHERE subject_id=?',(self.owner_a,))
        self.assertIsNone(read('shop-a',self.rid_a,self.owner_a))

    def test_nonverified_identity_cannot_read(self):
        self.db.execute('UPDATE bam_identities SET email_verified=0 '
            'WHERE subject_id=?',(self.owner_b,))
        query=draft_select_for_verified_member(
            tenant_id='shop-b',request_id=self.rid_b,
            verified_subject_id=self.owner_b)
        self.assertIsNone(self.query(query))

    def test_invalid_and_injection_looking_identifiers_fail_closed(self):
        cases=[
            {'tenant_id':'shop-a;DROP TABLE members;--'},
            {'tenant_id':'shop a'},
            {'tenant_id':''},
            {'request_id':'invalid'},
            {'request_id':self.rid_a.upper()},
            {'verified_subject_id':'../bad-user'},
            {'verified_subject_id':None},
        ]
        for change in cases:
            args=dict(tenant_id='shop-a',request_id=self.rid_a,
                verified_subject_id=self.owner_a)
            args.update(change)
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    draft_select_for_verified_member(**args)
                with self.assertRaises(ValueError):
                    calendar_select_for_verified_member(**args)

    def test_calendar_query_is_nonpublishing_and_scope_checked(self):
        q=calendar_select_for_verified_member(
            tenant_id='shop-a',request_id=self.rid_a,
            verified_subject_id=self.owner_a)
        self.assertIsNone(self.query(q))
        self.assertIsNone(summarize_calendar_row(None))
        self.assertIsNone(summarize_held_draft_row(None))
        with self.assertRaises(ValueError):
            summarize_calendar_row((self.rid_a,'time',1,'bad-token'))
        with self.assertRaises(ValueError):
            summarize_held_draft_row((self.rid_a,'facebook','copy',
                                      'approved_for_publish',1))


if __name__=='__main__':
    unittest.main()
