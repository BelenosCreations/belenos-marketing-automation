import sqlite3
import unittest
from truthguard_knowledge import TruthGuardKnowledge

class FactTemporalBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.store=TruthGuardKnowledge(sqlite3.connect(':memory:'))

    def approve(self,tenant='shop',now=200,expires_at=None):
        return self.store.approve(tenant_id=tenant,claim_key='hours',
            value='Open Thursday',source='owner-confirmed',approved_by='owner',
            now=now,expires_at=expires_at)

    def lookup(self,tenant='shop',now=200):
        return self.store.lookup(tenant_id=tenant,claim_key='hours',now=now)

    def test_future_approval_not_evidence(self):
        self.approve(now=200)
        self.assertEqual(self.lookup(now=199),[])

    def test_approval_active_at_approval_timestamp(self):
        self.approve(now=200)
        self.assertEqual(len(self.lookup(now=200)),1)

    def test_expired_fact_not_evidence(self):
        self.approve(now=200,expires_at=250)
        self.assertEqual(self.lookup(now=250),[])

    def test_other_business_isolated(self):
        self.approve(tenant='shop')
        self.assertEqual(self.lookup(tenant='other'),[])

    def test_revoked_fact_not_evidence(self):
        fact_id=self.approve(now=200)
        self.assertTrue(self.store.revoke(tenant_id='shop',fact_id=fact_id,now=201))
        self.assertEqual(self.lookup(now=202),[])

if __name__=='__main__': unittest.main()
