import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from optimizer import Candidate, curate, rank_slots, choose_balanced
TZ=ZoneInfo('America/New_York')

class OptimizerTests(unittest.TestCase):
    def item(self, **kwargs):
        args=dict(source_name='Example',source_url='https://example.com',original_url='https://example.com/post',category='education',summary='Print tip',source_approved=True,verified_facts=True)
        args.update(kwargs)
        return Candidate(**args)
    def test_trusted_link_only(self):
        self.assertEqual(curate(self.item())[0], 'eligible_link_only')
    def test_unapproved_source_requires_approval(self):
        self.assertEqual(curate(self.item(source_approved=False))[0], 'approval_required')
    def test_unverified_claim_requires_approval(self):
        self.assertEqual(curate(self.item(verified_facts=False))[0], 'approval_required')
    def test_sponsored_requires_approval(self):
        self.assertEqual(curate(self.item(sponsored=True))[0], 'approval_required')
    def test_bad_link_blocked(self):
        self.assertEqual(curate(self.item(original_url='javascript:alert(1)'))[0], 'blocked')
    def test_rank_activity_over_fixed_time(self):
        start=datetime(2026,11,10,8,tzinfo=TZ)
        scores={(1,10):14999,(1,12):14646,(1,18):12120}
        self.assertEqual(rank_slots(start=start,scores=scores,days=1)[0][0].hour,10)
    def test_respects_gap(self):
        start=datetime(2026,11,10,8,tzinfo=TZ)
        scores={(1,10):14999,(1,12):14646,(1,18):12120}
        ranked=rank_slots(start=start,scores=scores,days=1,occupied=[datetime(2026,11,10,10,tzinfo=TZ)])
        self.assertEqual(ranked[0][0].hour,18)
    def test_missing_scores_not_invented(self):
        self.assertEqual(rank_slots(start=datetime(2026,11,10,8,tzinfo=TZ),scores={},days=1),[])
    def test_daylight_saving(self):
        start=datetime(2027,3,13,8,tzinfo=TZ)
        result=rank_slots(start=start,scores={(5,10):1,(6,10):2},days=2)
        self.assertEqual(result[0][0].utcoffset(),timedelta(hours=-4))
    def test_category_balance(self):
        items=[self.item(category='education'),self.item(category='education'),self.item(category='creative_project')]
        chosen=choose_balanced(items,max_items=2)
        self.assertEqual(len(set(i.category for i in chosen)),2)
    def test_deadline(self):
        start=datetime(2026,11,10,8,tzinfo=TZ)
        scores={(1,10):1,(1,18):2}
        ranked=rank_slots(start=start,scores=scores,days=1,fixed_deadline=datetime(2026,11,10,12,tzinfo=TZ))
        self.assertEqual([x[0].hour for x in ranked],[10])

if __name__=='__main__': unittest.main()
