"""Local SQLite schema parity only; no customer facts can be exported."""
import sqlite3
import unittest
from business_curation import BusinessCuration
from analytics_sync_coordinator import AnalyticsSyncCoordinator
from audience_observation_store import AudienceObservationStore
from tenant_resources import TenantResources
from neon_business_analytics_schema import (
    BUSINESS_ANALYTICS_TABLES,business_analytics_ddl_preview,
    inspect_business_analytics_sqlite)
from neon_scoped_business_analytics import (
    prepare_business_sources_read,prepare_private_audience_read)


class BusinessAnalyticsPostgresPreviewTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.curation=BusinessCuration(self.db)
        self.audience=AudienceObservationStore(self.db)
        self.sync=AnalyticsSyncCoordinator(db=self.db,importer=object())
        self.resources=TenantResources(self.db)

    def tearDown(self):
        self.db.close()

    def test_seven_source_tables_and_foreign_keys_preview(self):
        report=inspect_business_analytics_sqlite(self.db)
        self.assertEqual(report['table_count'],7)
        self.assertEqual({r['table'] for r in report['tables']},
                         set(BUSINESS_ANALYTICS_TABLES))
        self.assertTrue(all(r['rows']==0 for r in report['tables']))
        self.assertFalse(report['source_rows_exported'])
        self.assertFalse(report['provider_access_enabled'])
        self.assertFalse(report['production_ready'])
        self.assertFalse(report['publishing_enabled'])
        ddls=business_analytics_ddl_preview()
        self.assertEqual(len(ddls),7)
        self.assertTrue(any('FOREIGN KEY(tenant_id,topic)' in d
                            for d in ddls))
        self.assertTrue(any('DOUBLE PRECISION' in d for d in ddls))

    def test_report_never_exposes_private_research_values(self):
        self.curation.create_profile('private-shop','Secret Label',
                                     'custom-products',['PrivateTopic'])
        self.curation.add_source(tenant_id='private-shop',
            source_url='https://test.example/private?key=123',
            source_name='SecretSource',topic='PrivateTopic')
        report=inspect_business_analytics_sqlite(self.db)
        for value in ('private-shop','Secret Label','PrivateTopic',
                      'test.example','SecretSource','key=123'):
            self.assertNotIn(value,str(report))
        self.assertEqual(next(x['rows'] for x in report['tables']
            if x['table']=='business_sources'),1)

    def test_schema_drift_fails_closed(self):
        self.db.execute('ALTER TABLE audience_observations ADD COLUMN leak TEXT')
        with self.assertRaisesRegex(ValueError,'audience_observations'):
            inspect_business_analytics_sqlite(self.db)

    def test_prepared_queries_have_no_input_interpolation(self):
        sql,params=prepare_business_sources_read(
            tenant_id='private-shop',verified_subject_id='ownerA')
        self.assertEqual(params,('private-shop','ownerA'))
        self.assertNotIn('private-shop',sql)
        self.assertIn('m.active=1',sql)
        sql,params=prepare_private_audience_read(
            tenant_id='private-shop',platform='facebook',
            verified_subject_id='ownerA')
        self.assertEqual(params,('private-shop','facebook','ownerA'))
        self.assertNotIn('ownerA',sql)
        self.assertIn("m.role='owner'",sql)
        for bad in ('','shop one','bad;DROP TABLE members','a\nb'):
            with self.assertRaises(ValueError):
                prepare_business_sources_read(
                    tenant_id=bad,verified_subject_id='ownerA')
            with self.assertRaises(ValueError):
                prepare_private_audience_read(
                    tenant_id='shop',platform=bad,
                    verified_subject_id='ownerA')


if __name__=='__main__':
    unittest.main()
