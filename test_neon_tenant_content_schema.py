"""Read-only local schema parity for tenant content and manual settings."""
import sqlite3
import unittest
from tenant_content import TenantContentStore
from scheduling_settings import SchedulingSettings
from neon_tenant_content_schema import (
    TENANT_CONTENT_TABLES,tenant_content_ddl_preview,
    inspect_tenant_content_sqlite)
from neon_scoped_tenant_content import (
    prepare_tenant_post_review,prepare_tenant_schedule_read)


class TenantContentPostgresPreviewTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.content=TenantContentStore(self.db)
        self.settings=SchedulingSettings(self.db,directory=None)

    def tearDown(self):
        self.db.close()

    def test_schema_parity_only_and_no_publish_action(self):
        report=inspect_tenant_content_sqlite(self.db)
        self.assertEqual(report['table_count'],4)
        self.assertEqual({x['table'] for x in report['tables']},
                         set(TENANT_CONTENT_TABLES))
        self.assertFalse(report['private_data_exported'])
        self.assertFalse(report['hosted_database_connected'])
        self.assertFalse(report['scheduled_jobs_created'])
        self.assertFalse(report['social_publishing_enabled'])
        self.assertFalse(report['production_ready'])
        preview=tenant_content_ddl_preview()
        self.assertEqual(len(preview),4)
        self.assertTrue(any('FOREIGN KEY(tenant_id,post_id)'
            in x for x in preview))
        self.assertFalse(any("'published'" in x for x in preview))

    def test_private_copy_never_exposed_in_schema_report(self):
        self.content.create_post('shop-a','draft-1','private content for tests',
                                 'promotion')
        self.content.create_event('shop-b','event-1','private event title')
        report=inspect_tenant_content_sqlite(self.db)
        for value in ('shop-a','shop-b','private content','private event title'):
            self.assertNotIn(value,str(report))
        self.assertEqual(next(x['rows'] for x in report['tables']
            if x['table']=='tenant_posts'),1)

    def test_source_drift_rejected(self):
        self.db.execute('ALTER TABLE scheduling_settings ADD COLUMN x TEXT')
        with self.assertRaisesRegex(ValueError,'scheduling_settings'):
            inspect_tenant_content_sqlite(self.db)

    def test_queries_are_parameterized_and_identity_scoped(self):
        sql,params=prepare_tenant_post_review(
            tenant_id='shop',post_id='draft1',verified_subject_id='ownerA')
        self.assertEqual(params,('shop','draft1','ownerA'))
        self.assertEqual(sql.count('%s'),3)
        self.assertNotIn('ownerA',sql)
        self.assertIn('a.tenant_id=p.tenant_id',sql)
        sql,params=prepare_tenant_schedule_read(
            tenant_id='shop',verified_subject_id='ownerA')
        self.assertEqual(params,('shop','ownerA'))
        self.assertIn("m.role='owner'",sql)
        for bad in ('','bad name','shop;drop','hello\nworld'):
            with self.assertRaises(ValueError):
                prepare_tenant_post_review(
                    tenant_id=bad,post_id='draft1',
                    verified_subject_id='ownerA')


if __name__=='__main__':
    unittest.main()
