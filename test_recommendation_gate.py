import sqlite3
import unittest
from optimizer import Candidate
from recommendation_gate import RecommendationGate

class RecommendationGateTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.gate=RecommendationGate(self.db)
        self.gate.sources.create_profile('belenos','Belenos','3d printing',['3d_printing'])
        self.gate.sources.create_profile('busy_b','Busy B','commercial cleaning',['facility_care'])
        self.url='https://example.org/maker'
        self.gate.sources.add_source(tenant_id='belenos',source_url=self.url,source_name='Maker',topic='3d_printing',approved=True)
        self.gate.creators.set_status(tenant_id='belenos',platform='youtube',account_id='maker123',status='approved',reason='noncompeting educator')
        self.candidate=Candidate(source_name='Maker',source_url=self.url,original_url=self.url+'/video',category='education',summary='Tips',source_approved=True,verified_facts=True)

    def check(self, **overrides):
        values=dict(tenant_id='belenos',topic='3d_printing',candidate=self.candidate,
                    platform='youtube',account_id='maker123',identity_verified=True,local_competitor_risk='cleared')
        values.update(overrides)
        return self.gate.evaluate(**values)

    def test_both_policies_allow_editorial_link(self):
        self.assertEqual(self.check()[0],'eligible_link_only')

    def test_unverified_identity_held(self):
        self.assertEqual(self.check(identity_verified=False)[0],'approval_required')

    def test_unknown_identity_held(self):
        self.assertEqual(self.check(account_id='other')[0],'approval_required')

    def test_known_competitor_blocked(self):
        self.gate.creators.set_status(tenant_id='belenos',platform='youtube',account_id='maker123',status='blocked',reason='competitor')
        self.assertEqual(self.check()[0],'blocked')

    def test_unapproved_source_held(self):
        self.gate.sources.add_source(tenant_id='belenos',source_url=self.url,source_name='Maker',topic='3d_printing',approved=False)
        self.assertEqual(self.check()[0],'approval_required')

    def test_possible_local_competitor_held(self):
        self.assertEqual(self.check(local_competitor_risk='possible')[0],'approval_required')

    def test_unknown_local_competitor_risk_held(self):
        self.assertEqual(self.check(local_competitor_risk='unknown')[0],'approval_required')

    def test_foreign_business_cannot_reuse_approval(self):
        self.assertNotEqual(self.check(tenant_id='busy_b',topic='facility_care')[0],'eligible_link_only')

    def test_url_block_overrides_identity_approval(self):
        self.gate.sources.block_competitor(tenant_id='belenos',source_url=self.url)
        self.assertEqual(self.check()[0],'blocked')

    def test_wrong_topic_denied(self):
        self.assertNotEqual(self.check(topic='facility_care')[0],'eligible_link_only')

if __name__=='__main__':
    unittest.main()
