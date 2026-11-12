"""Offline SQLite parity tests for session-authenticated inbox pagination."""
import hashlib
import sqlite3
import unittest

from neon_schema_blueprint import ddl_preview
from neon_session_inbox_contract import (
    prepare_session_inbox_page,summarize_inbox_page)


class SessionInboxContractTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        for ddl in ddl_preview():
            self.db.execute(ddl)
        self.token='Synthetic_Inbox_Session_For_Shop_A_1234567890123'
        self.digest=hashlib.sha256(self.token.encode('ascii')).hexdigest()
        for subject in ('owner-a','owner-b'):
            self.db.execute("""INSERT INTO bam_identities
                (subject_id,email,email_verified,active,created_at)
                VALUES (?,?,1,1,100)""",(subject,subject+'@example.test'))
        for tenant,subject in (('shop-a','owner-a'),('shop-b','owner-b')):
            self.db.execute("""INSERT INTO members
                (tenant_id,subject_id,role,active,revision)
                VALUES (?,?,'owner',1,1)""",(tenant,subject))
        self.db.execute("""INSERT INTO sessions
            (token_hash,subject_id,tenant_id,role,expires_at)
            VALUES (?,'owner-a','shop-a','owner',3600)""",(self.digest,))
        for tenant,request_id,created,status,copy in (
            ('shop-a','a'*32,100,'needs_content','A 1'),
            ('shop-a','b'*32,100,'ready_for_review','A 2'),
            ('shop-a','c'*32,101,'needs_content','A 3'),
            ('shop-b','d'*32,99,'needs_content','B private')):
            self.db.execute("""INSERT INTO content_requests
                (request_id,tenant_id,channel,draft_text,suggestion,
                 required_items,status,created_at,updated_at)
                VALUES (?,?,'facebook',?,'photo','[]',?,?,?)""",
                (request_id,tenant,copy,status,created,created))

    def tearDown(self):
        self.db.close()

    def page(self,**overrides):
        args={'raw_session_token':self.token,'tenant_id':'shop-a',
              'server_now':101,'limit':1}
        args.update(overrides)
        sql,params=prepare_session_inbox_page(**args)
        self.assertEqual(sql.count('%s'),len(params))
        self.assertNotIn(self.token,sql+str(params))
        rows=self.db.execute(sql.replace('%s','?'),params).fetchall()
        return summarize_inbox_page(rows,limit=args['limit'])

    def test_pagination_stable_with_equal_timestamps_and_no_cross_tenant(self):
        first=self.page()
        self.assertEqual([x['draft_text'] for x in first['items']],['A 1'])
        self.assertTrue(first['has_more'])
        self.assertEqual(first['next_cursor'],
                         {'created_at':100,'request_id':'a'*32})
        second=self.page(after_created_at=100,after_request_id='a'*32)
        self.assertEqual([x['draft_text'] for x in second['items']],['A 2'])
        third=self.page(after_created_at=100,after_request_id='b'*32)
        self.assertEqual([x['draft_text'] for x in third['items']],['A 3'])
        self.assertFalse(third['has_more'])
        self.assertIsNone(third['next_cursor'])
        self.assertFalse(third['publishing_enabled'])
        self.assertEqual(third['posts_scheduled'],0)
        self.assertEqual(self.page(tenant_id='shop-b')['items'],[])

    def test_status_filter_and_page_limit(self):
        result=self.page(status='needs_content',limit=50)
        self.assertEqual([x['draft_text'] for x in result['items']],
                         ['A 1','A 3'])
        self.assertFalse(result['has_more'])
        self.assertEqual(len(self.page(limit=2)['items']),2)

    def test_live_role_membership_identity_and_session_denials(self):
        self.db.execute("""UPDATE members SET role='viewer'
            WHERE tenant_id='shop-a' AND subject_id='owner-a'""")
        self.assertEqual(self.page()['items'],[])
        self.db.execute("""UPDATE members SET role='owner'
            WHERE tenant_id='shop-a' AND subject_id='owner-a'""")
        self.db.execute("""UPDATE members SET active=0
            WHERE tenant_id='shop-a' AND subject_id='owner-a'""")
        self.assertEqual(self.page()['items'],[])
        self.db.execute("""UPDATE members SET active=1
            WHERE tenant_id='shop-a' AND subject_id='owner-a'""")
        self.db.execute("""UPDATE bam_identities SET email_verified=0
            WHERE subject_id='owner-a'""")
        self.assertEqual(self.page()['items'],[])
        self.db.execute("""UPDATE bam_identities SET email_verified=1
            WHERE subject_id='owner-a'""")
        self.assertEqual(self.page(server_now=3600)['items'],[])
        self.db.execute("""UPDATE sessions SET revoked_at=101
            WHERE token_hash=?""",(self.digest,))
        self.assertEqual(self.page()['items'],[])

    def test_bad_input_rejected_without_sql_execution(self):
        base={'raw_session_token':self.token,'tenant_id':'shop-a',
              'server_now':101}
        for change in (
            {'raw_session_token':self.token+';'},
            {'raw_session_token':None},
            {'tenant_id':'shop-a OR true'},
            {'server_now':True},
            {'server_now':-1},
            {'limit':0},
            {'limit':51},
            {'limit':True},
            {'status':'needs_content OR true'},
            {'after_created_at':100},
            {'after_request_id':'a'*32},
            {'after_created_at':True,'after_request_id':'a'*32},
            {'after_created_at':100,'after_request_id':'not-id'},
        ):
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    prepare_session_inbox_page(**(base|change))

    def test_invalid_result_rows_are_not_displayed(self):
        for row in (
            [('a'*32,'facebook','A 1','needs_content',1,True)],
            [('invalid','facebook','A 1','needs_content',1,100)],
            [('a'*32,'facebook','A 1','published',1,100)],
        ):
            with self.assertRaises(ValueError):
                summarize_inbox_page(row,limit=1)
        with self.assertRaises(ValueError):
            summarize_inbox_page([
                ('b'*32,'facebook','B','needs_content',1,100),
                ('a'*32,'facebook','A','needs_content',1,100)],limit=2)


if __name__=='__main__':
    unittest.main()
