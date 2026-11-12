"""Zero-network SQLite-to-Neon identity/draft schema planning regressions."""
import sqlite3
import unittest
from bam_offline_gateway import BAMOfflineGateway
from neon_schema_blueprint import (TABLE_NAMES,ddl_preview,
    inspect_sqlite_subset,assert_never_execute_preview)


class NeonSchemaBlueprintTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.app=BAMOfflineGateway(self.db,enabled=True,clock=lambda:101)
    def tearDown(self):
        self.db.close()

    def test_core_schema_matches_offline_gateway_and_contains_no_data(self):
        report=inspect_sqlite_subset(self.db)
        self.assertEqual(report['subset_table_count'],9)
        self.assertEqual({row['table'] for row in report['tables']},
                         set(TABLE_NAMES))
        self.assertEqual({row['rows'] for row in report['tables']},{0})
        self.assertFalse(report['production_ready'])
        self.assertFalse(report['live_migration_performed'])
        self.assertFalse(report['postgres_connection_attempted'])
        self.assertFalse(report['data_exported'])
        self.assertFalse(report['publishing_enabled'])
        self.assertEqual(len(report['schema_contract_digest']),64)
        self.assertNotIn('postgresql://',str(report))

    def test_never_exports_private_rows_even_when_populated(self):
        self.app.directory.bootstrap_owner('shop','test-owner')
        self.app.directory.bootstrap_owner('other','different-owner')
        token=self.app.sessions.issue(
            self.app.directory.resolve('shop','test-owner'),now=100)
        secret_copy='secret draft copy must stay private'
        self.app.requests.create(tenant_id='shop',channel='facebook',
            draft_text=secret_copy,suggestion='photo',required_items=['image'],
            now=101)
        report=inspect_sqlite_subset(self.db)
        self.assertEqual(next(row['rows'] for row in report['tables']
             if row['table']=='members'),2)
        self.assertEqual(next(row['rows'] for row in report['tables']
             if row['table']=='content_requests'),1)
        self.assertNotIn(secret_copy,str(report))
        self.assertNotIn(token,str(report))
        self.assertNotIn('test-owner',str(report))

    def test_schema_drift_fails_closed(self):
        self.db.execute('ALTER TABLE members ADD COLUMN unexpected TEXT')
        with self.assertRaisesRegex(ValueError,'members'):
            inspect_sqlite_subset(self.db)

    def test_ddl_is_explicit_and_has_no_remote_execution(self):
        ddl=ddl_preview()
        self.assertEqual(len(ddl),9)
        self.assertTrue(ddl[0].startswith('CREATE TABLE bam_identities'))
        self.assertTrue(any('BYTEA' in sql for sql in ddl))
        self.assertTrue(any('UNIQUE(tenant_id,utc_at)' in sql for sql in ddl))
        self.assertFalse(any('CREATE EXTENSION' in sql for sql in ddl))
        with self.assertRaises(PermissionError):
            assert_never_execute_preview(enabled=True)

    def test_requires_real_sqlite_not_untrusted_fake_connection(self):
        with self.assertRaises(TypeError):
            inspect_sqlite_subset(object())


if __name__=='__main__':
    unittest.main()
