import sqlite3
import unittest
from audience_observation_store import AudienceObservationStore
from audience_schedule_ranker import rank_candidates

class AudienceObservationStoreTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.store=AudienceObservationStore(self.db)

    def add(self,**changes):
        values=dict(tenant_id='shop',platform='facebook',source_post_id='post1',
                    candidate='morning',engagement_rate=.25,
                    measured_at=100,source_name='offline_import')
        values.update(changes)
        return self.store.ingest_trusted(**values)

    def query(self,**changes):
        values=dict(tenant_id='shop',platform='facebook',
                    candidates=['morning'],since=0,until=200)
        values.update(changes)
        return self.store.for_candidates(**values)

    def test_ingestion_and_windowed_query(self):
        self.add()
        self.assertEqual(len(self.query()),1)
        self.assertEqual(self.query(since=101),[])

    def test_cross_tenant_and_platform_isolation(self):
        self.add()
        self.assertEqual(self.query(tenant_id='other'),[])
        self.assertEqual(self.query(platform='instagram'),[])

    def test_duplicate_source_rejected(self):
        self.add()
        with self.assertRaises(sqlite3.IntegrityError):
            self.add()

    def test_same_post_id_on_different_platform_allowed(self):
        self.add()
        self.add(platform='instagram')
        self.assertEqual(len(self.query()),1)
        self.assertEqual(len(self.query(platform='instagram')),1)

    def test_invalid_rate_rejected(self):
        with self.assertRaises(ValueError):
            self.add(engagement_rate=float('nan'))

    def test_invalid_window_rejected(self):
        with self.assertRaises(ValueError):
            self.query(since=201,until=200)

    def test_observations_feed_ranker_without_cross_tenant_mix(self):
        for index in range(5):
            self.add(source_post_id='morning'+str(index),
                     candidate='morning',engagement_rate=.2)
            self.add(source_post_id='evening'+str(index),
                     candidate='evening',engagement_rate=.7)
        records=self.query(candidates=['morning','evening'])
        result=rank_candidates(tenant_id='shop',
            candidates=['morning','evening'],observations=records)
        self.assertEqual(result['selection'],'evening')
        self.assertFalse(result['publishing_enabled'])

if __name__=='__main__':unittest.main()
