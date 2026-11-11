import sqlite3
import unittest
from truthguard_knowledge import TruthGuardKnowledge
from truthguard_review import TruthGuardReviewer

class TruthGuardTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.knowledge=TruthGuardKnowledge(self.db)
        self.reviewer=TruthGuardReviewer(self.knowledge)
        self.fact=self.knowledge.approve(tenant_id='belenos',
            claim_key='product',value='Custom resin-printed artwork',
            source='owner-confirmed catalog',approved_by='owner',now=100,
            expires_at=200)
        self.claim={'key':'product','text':'Custom resin-printed artwork'}

    def test_verified_exact_claim(self):
        r=self.reviewer.review_claims(tenant_id='belenos',
            claims=[self.claim],now=101)
        self.assertEqual(r['claims'][0]['status'],'verified')
        self.assertEqual(r['claims'][0]['sources'][0]['fact_id'],self.fact)

    def test_case_whitespace_normalized(self):
        r=self.reviewer.review_claims(tenant_id='belenos',
            claims=[{'key':'product','text':'  CUSTOM  resin-printed artwork '}],now=101)
        self.assertEqual(r['claims'][0]['status'],'verified')

    def test_invented_claim_held(self):
        r=self.reviewer.review_claims(tenant_id='belenos',
            claims=[{'key':'product','text':'Waterproof for 50 years'}],now=101)
        self.assertEqual(r['status'],'held')

    def test_other_business_isolated(self):
        r=self.reviewer.review_claims(tenant_id='busy-b',
            claims=[self.claim],now=101)
        self.assertEqual(r['status'],'held')

    def test_expired_fact_not_usable(self):
        r=self.reviewer.review_claims(tenant_id='belenos',
            claims=[self.claim],now=200)
        self.assertEqual(r['status'],'held')

    def test_revoked_fact_not_usable(self):
        self.assertTrue(self.knowledge.revoke(tenant_id='belenos',
            fact_id=self.fact,now=105))
        r=self.reviewer.review_claims(tenant_id='belenos',
            claims=[self.claim],now=106)
        self.assertEqual(r['status'],'held')

    def test_wrong_tenant_cannot_revoke(self):
        self.assertFalse(self.knowledge.revoke(tenant_id='busy-b',
            fact_id=self.fact,now=101))
        self.assertEqual(self.reviewer.review_claims(tenant_id='belenos',
            claims=[self.claim],now=102)['status'],'verified')

    def test_multiple_claims_fail_closed(self):
        r=self.reviewer.review_claims(tenant_id='belenos',claims=[
            self.claim,{'key':'hours','text':'Open 24 hours'}],now=101)
        self.assertEqual(r['status'],'held')

    def test_no_claims_not_verified(self):
        self.assertEqual(self.reviewer.review_claims(
            tenant_id='belenos',claims=[],now=101)['status'],'held')

    def test_draft_always_held_until_extraction_gate(self):
        r=self.reviewer.review_draft(tenant_id='belenos',
            draft_text='Custom resin-printed artwork',claims=[self.claim],
            now=101,extraction_complete=True)
        self.assertEqual(r['status'],'held')
        self.assertFalse(r['publishing_enabled'])

    def test_invalid_fact_provenance_rejected(self):
        with self.assertRaises(ValueError):
            self.knowledge.approve(tenant_id='belenos',claim_key='hours',
                value='9-5',source='',approved_by='owner',now=101)

    def test_invalid_claim_rejected(self):
        with self.assertRaises(ValueError):
            self.reviewer.review_claims(tenant_id='belenos',
                claims=[{'key':'product','text':''}],now=101)

if __name__=='__main__':unittest.main()
