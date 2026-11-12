"""No-secret SQLite parity tests for the next seven PG schema previews."""
import sqlite3
import unittest
from bam_offline_gateway import BAMOfflineGateway
from oauth_attempt_ledger import OAuthAttemptLedger
from neon_identity_provider_schema import (
    EXTRA_TABLE_NAMES,identity_provider_ddl_preview,
    inspect_identity_provider_sqlite)
from neon_scoped_provider_queries import (
    prepare_connections_read,prepare_personal_ai_usage,
    safe_connection_preview)

class ProviderAISchemaTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.app=BAMOfflineGateway(self.db,enabled=False)
        OAuthAttemptLedger(self.db)
    def tearDown(self):
        self.db.close()

    def test_seven_table_source_parity_and_no_data_export(self):
        info=inspect_identity_provider_sqlite(self.db)
        self.assertEqual(info['table_count'],7)
        self.assertEqual({v['table'] for v in info['tables']},
                         set(EXTRA_TABLE_NAMES))
        self.assertFalse(info['secrets_exposed'])
        self.assertFalse(info['provider_connected'])
        self.assertFalse(info['migration_executed'])
        self.assertFalse(info['production_ready'])
        self.assertFalse(info['publishing_enabled'])
        self.assertEqual(len(identity_provider_ddl_preview()),7)

    def test_private_secret_refs_are_never_returned(self):
        self.db.execute("""INSERT INTO provider_connections
            (tenant_id,platform,account_id,vault_reference,scope,state,
             expires_at,updated_at)
            VALUES ('shop','facebook','page','vault:example-private-ref',
                    'read_insights','pending',NULL,101)""")
        report=inspect_identity_provider_sqlite(self.db)
        self.assertEqual(next(row['rows'] for row in report['tables']
            if row['table']=='provider_connections'),1)
        self.assertNotIn('vault:example-private-ref',str(report))
        self.assertNotIn('shop',str(report))

    def test_drift_detected(self):
        self.db.execute('ALTER TABLE bam_ai_usage ADD COLUMN unexpected TEXT')
        with self.assertRaisesRegex(ValueError,'bam_ai_usage'):
            inspect_identity_provider_sqlite(self.db)

    def test_connection_query_no_vault_column_or_publication(self):
        sql,params=prepare_connections_read(
            tenant_id='shop',verified_subject_id='member')
        self.assertEqual(params,('shop','member'))
        self.assertNotIn('vault_reference',sql)
        self.assertIn('i.email_verified=1',sql)
        receipt=safe_connection_preview(
            ('facebook','page','read_insights','pending',None))
        self.assertFalse(receipt['publishing_enabled'])
        self.assertFalse(receipt['live_provider_verified'])
        self.assertNotIn('vault_reference',str(receipt))
        with self.assertRaises(ValueError):
            safe_connection_preview(('fb','page','scope','pending','bad'))

    def test_usage_query_scopes_to_person_and_month(self):
        sql,params=prepare_personal_ai_usage(
            tenant_id='shop',verified_subject_id='member',month='2026-11')
        self.assertEqual(params,('shop','member','2026-11'))
        self.assertNotIn('shop',sql)
        self.assertIn('u.subject_id=%s',sql)
        for bad in ('2026-13','2026-00','../2026-11','2026-11;DROP'):
            with self.assertRaises(ValueError):
                prepare_personal_ai_usage(tenant_id='shop',
                    verified_subject_id='member',month=bad)


if __name__=='__main__':
    unittest.main()
