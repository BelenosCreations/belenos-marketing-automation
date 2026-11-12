"""Owner-private team roster SQL parity and negative authorization tests."""
import hashlib
import sqlite3
import unittest

from neon_schema_blueprint import ddl_preview
from neon_session_team_contract import (
    prepare_session_owner_team_roster,summarize_owner_team_roster)


class SessionOwnerTeamTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        for ddl in ddl_preview():
            self.db.execute(ddl)
        self.token='Synthetic_Owner_Team_Session_1234567890123456'
        self.digest=hashlib.sha256(self.token.encode('ascii')).hexdigest()
        for subject,verified,active in (
            ('owner-a',1,1),('viewer-a',0,1),
            ('owner-b',1,1),('viewer-b',1,1)):
            self.db.execute("""INSERT INTO bam_identities
                (subject_id,email,email_verified,active,created_at)
                VALUES (?,?,?,?,100)""",
                (subject,subject+'@example.test',verified,active))
        for tenant,subject,role,active in (
            ('shop-a','owner-a','owner',1),
            ('shop-a','viewer-a','viewer',1),
            ('shop-b','owner-b','owner',1),
            ('shop-b','viewer-b','viewer',1)):
            self.db.execute("""INSERT INTO members
                (tenant_id,subject_id,role,active,revision)
                VALUES (?,?,?,?,1)""",(tenant,subject,role,active))
        self.db.execute("""INSERT INTO sessions
            (token_hash,subject_id,tenant_id,role,expires_at)
            VALUES (?,'owner-a','shop-a','owner',3600)""",(self.digest,))

    def tearDown(self):
        self.db.close()

    def roster(self,**overrides):
        args={'raw_session_token':self.token,'tenant_id':'shop-a',
              'server_now':101}
        args.update(overrides)
        sql,params=prepare_session_owner_team_roster(**args)
        self.assertEqual(sql.count('%s'),len(params))
        self.assertNotIn(self.token,sql+str(params))
        rows=self.db.execute(sql.replace('%s','?'),params).fetchall()
        return summarize_owner_team_roster(rows,tenant_id=args['tenant_id'])

    def test_owner_sees_only_their_team_with_redacted_unverified_email(self):
        roster=self.roster()
        self.assertEqual(roster['tenant_id'],'shop-a')
        self.assertEqual(len(roster['members']),2)
        self.assertEqual([m['member_id'] for m in roster['members']],
                         ['owner-a','viewer-a'])
        self.assertTrue(roster['members'][0]['is_self'])
        self.assertEqual(roster['members'][0]['email'],'owner-a@example.test')
        self.assertIsNone(roster['members'][1]['email'])
        self.assertFalse(roster['publishing_enabled'])
        self.assertNotIn('owner-b',str(roster))
        self.assertNotIn('viewer-b',str(roster))

    def test_inactive_members_remain_visible_but_private(self):
        self.db.execute("""UPDATE members SET active=0,revision=2
            WHERE subject_id='viewer-a' AND tenant_id='shop-a'""")
        roster=self.roster()
        viewer=roster['members'][1]
        self.assertEqual(viewer['revision'],2)
        self.assertFalse(viewer['active'])
        self.assertFalse(viewer['is_self'])

    def test_nonowner_crossbusiness_stale_revoked_and_expired_denied(self):
        self.assertRaises(PermissionError,self.roster,tenant_id='shop-b')
        self.assertRaises(PermissionError,self.roster,server_now=3600)
        self.db.execute("""UPDATE members SET role='viewer'
            WHERE tenant_id='shop-a' AND subject_id='owner-a'""")
        self.assertRaises(PermissionError,self.roster)
        self.db.execute("""UPDATE members SET role='owner'
            WHERE tenant_id='shop-a' AND subject_id='owner-a'""")
        self.db.execute("""UPDATE bam_identities SET email_verified=0
            WHERE subject_id='owner-a'""")
        self.assertRaises(PermissionError,self.roster)
        self.db.execute("""UPDATE bam_identities SET email_verified=1
            WHERE subject_id='owner-a'""")
        self.db.execute('UPDATE sessions SET revoked_at=101 WHERE token_hash=?',
                        (self.digest,))
        self.assertRaises(PermissionError,self.roster)

    def test_malformed_inputs_and_rows_refused(self):
        base={'raw_session_token':self.token,'tenant_id':'shop-a',
              'server_now':101}
        for change in (
            {'raw_session_token':None},
            {'raw_session_token':self.token+';'},
            {'tenant_id':'shop-a;DROP'},
            {'server_now':True},
            {'server_now':-1},
        ):
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    prepare_session_owner_team_roster(**(base|change))
        for row in (
            [('owner-a','owner',1,0,'owner@example.test',1)],
            [('owner-a','owner',1,1,'owner@example.test',0)],
            [('owner-a','viewer',1,1,'owner@example.test',1)],
            [('owner-a','owner',1,1,'owner@example.test',1)]*2,
        ):
            with self.assertRaises((ValueError,PermissionError)):
                summarize_owner_team_roster(row,tenant_id='shop-a')
        with self.assertRaises(RuntimeError):
            summarize_owner_team_roster([
                ('owner-a','owner',1,1,'owner@example.test',1)]*201,
                tenant_id='shop-a')


if __name__=='__main__':
    unittest.main()
