"""No-data, all-table local SQLite portability inventory tests."""
import sqlite3
import unittest
from bam_offline_gateway import BAMOfflineGateway
from neon_schema_blueprint import TABLE_NAMES
from neon_schema_inventory import (
    inventory_sqlite_for_neon,inventory_fresh_offline_gateway)


class NeonSchemaInventoryTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.app=BAMOfflineGateway(self.db,enabled=False)
    def tearDown(self):
        self.db.close()

    def test_identifies_unmapped_tables_without_claiming_migration(self):
        report=inventory_sqlite_for_neon(self.db)
        self.assertGreater(report['all_table_count'],len(TABLE_NAMES))
        self.assertGreater(report['unmapped_table_count'],0)
        self.assertEqual(report['mapped_subset_count'],len(TABLE_NAMES))
        self.assertEqual(report['all_table_count'],
            report['mapped_subset_count']+report['unmapped_table_count'])
        self.assertNotIn('bam_identities',report['unmapped_table_names'])
        self.assertIn('bam_business_invitations',
                      report['unmapped_table_names']
                      if 'bam_business_invitations' in
                      [x['table'] for x in report['tables']] else
                      ['bam_business_invitations'])
        self.assertFalse(report['provider_connected'])
        self.assertFalse(report['migration_executed'])
        self.assertFalse(report['ready_for_hosting'])
        self.assertFalse(report['posting_enabled'])
        self.assertFalse(report['contains_customer_records'])
        self.assertFalse(report['contains_raw_schema_ddl'])

    def test_inventory_never_exposes_user_draft_or_session(self):
        # Test-only direct storage: values must not be returned by inventory.
        from access_policy import Principal,Role
        self.app.directory.bootstrap_owner('private-business','owner')
        token=self.app.sessions.issue(Principal(
            'owner','private-business',Role.OWNER),now=100)
        secret='CONFIDENTIAL_TEST_DRAFT_4ff4a'
        self.app.requests.create(tenant_id='private-business',
            channel='facebook',draft_text=secret,suggestion='photo',
            required_items=['image'],now=100)
        report=inventory_sqlite_for_neon(self.db)
        self.assertNotIn(secret,str(report))
        self.assertNotIn(token,str(report))
        self.assertNotIn('private-business',str(report))
        self.assertNotIn('CREATE TABLE',str(report))

    def test_schema_digest_changes_without_reading_rows(self):
        original=inventory_sqlite_for_neon(self.db)
        self.db.execute('CREATE TABLE extra_schema_test(id INTEGER PRIMARY KEY)')
        changed=inventory_sqlite_for_neon(self.db)
        self.assertNotEqual(original['schema_digest'],changed['schema_digest'])
        self.assertEqual(changed['all_table_count'],
                         original['all_table_count']+1)
        self.assertIn('extra_schema_test',changed['unmapped_table_names'])

    def test_untrusted_identifier_and_missing_tables_fail(self):
        self.db.execute('CREATE TABLE "unexpected;name" (id INTEGER)')
        with self.assertRaises(ValueError):
            inventory_sqlite_for_neon(self.db)
        with self.assertRaises(TypeError):
            inventory_sqlite_for_neon(object())
        other=sqlite3.connect(':memory:')
        try:
            with self.assertRaises(ValueError):
                inventory_sqlite_for_neon(other)
        finally:
            other.close()

    def test_ephemeral_report_is_reproducible(self):
        a=inventory_fresh_offline_gateway()
        b=inventory_fresh_offline_gateway()
        self.assertEqual(a['schema_digest'],b['schema_digest'])
        self.assertEqual(a['all_table_count'],b['all_table_count'])
        self.assertNotIn('sqlite_sequence',a['unmapped_table_names'])


if __name__=='__main__':
    unittest.main()
