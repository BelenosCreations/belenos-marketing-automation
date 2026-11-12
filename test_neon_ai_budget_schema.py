"""Local SQLite source parity + no-paid-AI rules for schema stage four."""
import sqlite3
import unittest
from bam_offline_gateway import BAMOfflineGateway
from ai_generation_idempotency import AIGenerationIdempotency
from ai_sponsorship import SponsoredAIQuota
from neon_ai_budget_schema import (
    BUDGET_TABLE_NAMES,ai_budget_ddl_preview,
    inspect_ai_budget_sqlite)

class NeonAIBudgetSchemaTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.app=BAMOfflineGateway(self.db,enabled=False)
        AIGenerationIdempotency(db=self.db,policy_store=self.app.ai_policy)
        SponsoredAIQuota(db=self.db,policy_store=self.app.ai_policy)
    def tearDown(self):
        self.db.close()

    def test_existing_sqlite_columns_match_explicit_previews(self):
        report=inspect_ai_budget_sqlite(self.db)
        self.assertEqual(report['table_count'],8)
        self.assertEqual({row['table'] for row in report['tables']},
                         set(BUDGET_TABLE_NAMES))
        self.assertEqual(report['user_usage_columns'],6)
        self.assertFalse(report['provider_traffic'])
        self.assertFalse(report['real_cost_reconciliation'])
        self.assertFalse(report['production_ready'])
        self.assertFalse(report['data_exported'])
        self.assertFalse(report['publishing_enabled'])

    def test_private_cost_rows_are_never_in_schema_preflight(self):
        self.db.execute("""INSERT INTO bam_ai_business_facts
             (tenant_id,facts_json,revision,confirmed_by,confirmed_at)
             VALUES ('private-shop','{"secret":"test"}',1,'owner',100)""")
        report=inspect_ai_budget_sqlite(self.db)
        self.assertNotIn('private-shop',str(report))
        self.assertNotIn('secret',str(report))
        self.assertNotIn('owner',str(report))
        self.assertEqual(next(row['rows'] for row in report['tables']
            if row['table']=='bam_ai_business_facts'),1)

    def test_stage_four_has_cost_deduplication_and_paused_default(self):
        sql=ai_budget_ddl_preview()
        self.assertEqual(len(sql),13)
        self.assertIn('ADD COLUMN reserved_micro_usd',sql[0])
        self.assertIn('ADD COLUMN unpriced_requests',sql[1])
        self.assertTrue(any('CREATE UNIQUE INDEX bam_ai_cost_trusted_ref'
                            in s for s in sql))
        self.assertTrue(sql[-1].endswith('VALUES (1,1,0)'))

    def test_source_drift_fails_closed(self):
        self.db.execute('ALTER TABLE bam_ai_cost_events ADD COLUMN drift TEXT')
        with self.assertRaisesRegex(ValueError,'bam_ai_cost_events'):
            inspect_ai_budget_sqlite(self.db)

if __name__=='__main__':
    unittest.main()
