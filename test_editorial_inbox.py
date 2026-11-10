import sqlite3
import unittest
from optimizer import Candidate
from recommendation_gate import RecommendationGate
from editorial_inbox import EditorialInbox

class EditorialInboxTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.gate=RecommendationGate(self.db)
        self.inbox=EditorialInbox(self.db,self.gate)
        self.gate.sources.create_profile('belenos','Belenos','printing',['3d_printing'])
        self.gate.sources.create_profile('busy_b','Busy B','cleaning',['facility_care'])
        self.url='https://example.org/creator'
        self.gate.sources.add_source(tenant_id='belenos',source_url=self.url,source_name='Maker',topic='3d_printing',approved=True)
        self.gate.creators.set_status(tenant_id='belenos',platform='youtube',account_id='maker',status='approved',reason='educator')
        self.candidate=Candidate(source_name='Maker',source_url=self.url,original_url=self.url+'/video',category='education',summary='Print tips',source_approved=True,verified_facts=True)

    def consider(self,**overrides):
        args=dict(tenant_id='belenos',topic='3d_printing',candidate=self.candidate,
                  platform='youtube',account_id='maker',identity_verified=True,local_competitor_risk='cleared')
        args.update(overrides)
        return self.inbox.consider(**args)

    def test_eligible_item_still_requires_review(self):
        self.assertEqual(self.consider()[0],'review')
        self.assertEqual(self.inbox.list_for_business('belenos')[0][3],'review')

    def test_other_business_cannot_see_item(self):
        self.consider()
        self.assertEqual(self.inbox.list_for_business('busy_b'),[])

    def test_known_competitor_not_enqueued(self):
        self.gate.creators.set_status(tenant_id='belenos',platform='youtube',account_id='maker',status='blocked',reason='competitor')
        self.assertEqual(self.consider()[0],'blocked')
        self.assertEqual(self.inbox.list_for_business('belenos'),[])

    def test_blocked_rescreen_removes_prior_queue_entry(self):
        self.consider()
        self.gate.creators.set_status(tenant_id='belenos',platform='youtube',account_id='maker',status='blocked',reason='competitor')
        self.assertEqual(self.consider()[0],'blocked')
        self.assertEqual(self.inbox.list_for_business('belenos'),[])

    def test_unknown_creator_held_for_review(self):
        self.assertEqual(self.consider(account_id='unknown')[0],'review')

    def test_duplicate_link_idempotent(self):
        self.consider();self.consider()
        self.assertEqual(len(self.inbox.list_for_business('belenos')),1)

    def test_unverified_creator_not_publishable(self):
        self.assertEqual(self.consider(identity_verified=False)[0],'review')
        self.assertNotIn('published',str(self.inbox.list_for_business('belenos')))

    def recheck(self, **overrides):
        args=dict(tenant_id='belenos',topic='3d_printing',candidate=self.candidate,
                  platform='youtube',account_id='maker',identity_verified=True,
                  local_competitor_risk='cleared')
        args.update(overrides)
        return self.inbox.recheck_for_editorial_review(**args)

    def test_recheck_requires_queued_item(self):
        self.assertEqual(self.recheck()[0],'blocked')

    def test_recheck_eligible_requires_human_review(self):
        self.consider()
        self.assertEqual(self.recheck()[0],'eligible_for_human_review')

    def test_recheck_revoked_creator_is_blocked_and_removed(self):
        self.consider()
        self.gate.creators.set_status(tenant_id='belenos',platform='youtube',
                                      account_id='maker',status='blocked',reason='competitor')
        self.assertEqual(self.recheck()[0],'blocked')
        self.assertEqual(self.inbox.list_for_business('belenos'),[])

    def test_recheck_unverified_identity_held(self):
        self.consider()
        self.assertEqual(self.recheck(identity_verified=False)[0],'approval_required')

    def test_recheck_unknown_competitor_status_held(self):
        self.consider()
        self.assertEqual(self.recheck(local_competitor_risk='unknown')[0],'approval_required')

    def test_recheck_cross_business_denied(self):
        self.consider()
        self.assertEqual(self.recheck(tenant_id='busy_b')[0],'blocked')

    def test_recheck_wrong_creator_denied(self):
        self.consider()
        self.assertEqual(self.recheck(account_id='impostor')[0],'blocked')

    def test_recheck_wrong_topic_denied(self):
        self.consider()
        self.assertEqual(self.recheck(topic='facility_care')[0],'blocked')

    def test_invalid_tenant_denied(self):
        with self.assertRaises(ValueError):self.consider(tenant_id='')

    def test_possible_competitor_requires_review(self):
        self.assertEqual(self.consider(local_competitor_risk='possible')[0],'review')

if __name__=='__main__':unittest.main()
