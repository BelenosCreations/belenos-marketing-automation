"""No-secret SQLite DDL parity test for private editorial/security ledgers."""
import sqlite3
import unittest
from editorial_attestations import EditorialAttestations
from editorial_inbox import EditorialInbox
from approval_intent_service import ApprovalIntentService
from truthguard_knowledge import TruthGuardKnowledge
from creator_identities import CreatorIdentityPolicy
from email_credential_recovery import EmailCredentialRecovery
from neon_review_security_schema import (
    REVIEW_SECURITY_TABLES,review_security_ddl_preview,
    inspect_review_security_sqlite)
from neon_scoped_review_facts import prepare_current_private_facts


class ReviewSecurityPortabilityTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        EditorialAttestations(self.db)
        EditorialInbox(self.db,recommendation_gate=None)
        ApprovalIntentService(db=self.db,sessions=None,directory=None,
                              content_service=None)
        TruthGuardKnowledge(self.db)
        CreatorIdentityPolicy(self.db)
        EmailCredentialRecovery(db=self.db,auth=None,
                                deliver=lambda *a,**k:None)
    def tearDown(self):
        self.db.close()

    def test_six_source_tables_match_pg_preview(self):
        report=inspect_review_security_sqlite(self.db)
        self.assertEqual(report['table_count'],6)
        self.assertEqual({r['table'] for r in report['tables']},
                         set(REVIEW_SECURITY_TABLES))
        self.assertFalse(report['secret_data_exported'])
        self.assertFalse(report['real_email_delivery_enabled'])
        self.assertFalse(report['publish_permission_granted'])
        self.assertFalse(report['production_ready'])
        preview=review_security_ddl_preview()
        self.assertEqual(len(preview),7)
        self.assertTrue(any('CHECK(status IN' in s for s in preview))
        self.assertTrue(any('CREATE INDEX truthguard_facts_lookup'
                            in s for s in preview))

    def test_security_data_is_not_reported(self):
        self.db.execute("""INSERT INTO bam_email_actions
            (token_hash,subject_id,purpose,expires_at)
            VALUES (?,?,?,?)""",('a'*64,'secret_member','reset',100))
        self.db.execute("""INSERT INTO truthguard_facts
            (tenant_id,fact_id,claim_key,value,source,approved_by,approved_at)
            VALUES ('private-tenant','f','hours','private_value',
                    'private_url','owner',100)""")
        report=inspect_review_security_sqlite(self.db)
        for private in ('secret_member','private_value','private_url',
                        'private-tenant','a'*64):
            self.assertNotIn(private,str(report))

    def test_source_drift_rejected(self):
        self.db.execute('ALTER TABLE editorial_inbox ADD COLUMN drift TEXT')
        with self.assertRaisesRegex(ValueError,'editorial_inbox'):
            inspect_review_security_sqlite(self.db)

    def test_private_fact_query_is_prepared_and_unspoofable(self):
        sql,params=prepare_current_private_facts(
            tenant_id='tenantA',verified_subject_id='ownerA',server_now=100)
        self.assertEqual(params,('tenantA','ownerA',100))
        self.assertEqual(sql.count('%s'),3)
        self.assertIn('f.revoked_at IS NULL',sql)
        self.assertNotIn('tenantA',sql)
        for changed in (
            {'tenant_id':'other;DROP'},
            {'verified_subject_id':'bad actor'},
            {'server_now':True},
            {'server_now':-1}):
            args=dict(tenant_id='tenantA',verified_subject_id='ownerA',
                      server_now=100)
            args.update(changed)
            with self.assertRaises(ValueError):
                prepare_current_private_facts(**args)

if __name__=='__main__':
    unittest.main()
