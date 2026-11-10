import unittest
from audience_schedule_ranker import rank_candidates
from schedule_preview import preview_schedule
from test_schedule_readiness import FakeLedger

class AudienceRankerTests(unittest.TestCase):
    def observations(self):
        return ([dict(tenant_id='shop',candidate='late',engagement_rate=.8)]*5+
                [dict(tenant_id='shop',candidate='early',engagement_rate=.2)]*5)
    def rank(self,**kwargs):
        args=dict(tenant_id='shop',candidates=['early','late'],
                  observations=self.observations())
        args.update(kwargs)
        return rank_candidates(**args)
    def test_observed_mean_selects_late(self):
        self.assertEqual(self.rank()['selection'],'late')
    def test_insufficient_data_is_not_predicted(self):
        result=self.rank(observations=self.observations()[:3])
        self.assertIsNone(result['selection'])
        self.assertIsNone(result['ranked'][0]['observed_mean'])
    def test_cross_tenant_rejected(self):
        with self.assertRaises(PermissionError):
            self.rank(observations=[dict(tenant_id='other',candidate='early',
                                        engagement_rate=.5)])
    def test_invalid_engagement_rejected(self):
        with self.assertRaises(ValueError):
            self.rank(observations=[dict(tenant_id='shop',candidate='early',
                                        engagement_rate=float('nan'))])
    def test_unrecognized_candidate_rejected(self):
        with self.assertRaises(ValueError):
            self.rank(observations=[dict(tenant_id='shop',candidate='other',
                                        engagement_rate=.5)])
    def test_smart_preview_selects_observed_slot_but_remains_held(self):
        times=['2026-11-11T10:00','2026-11-11T18:30']
        obs=([dict(tenant_id='shop',candidate=times[0],engagement_rate=.1)]*5+
             [dict(tenant_id='shop',candidate=times[1],engagement_rate=.7)]*5)
        result=preview_schedule(ledger=FakeLedger(),token='owner',
            tenant_id='shop',intent_id='id',mode='smart',
            timezone_name='America/New_York',smart_candidates=times,
            observations=obs,now=100)
        self.assertEqual(result['selection_policy'],'highest_observed_mean')
        self.assertEqual(result['ranking']['selection'],times[1])
        self.assertFalse(result['scheduled_job_created'])
    def test_manual_mode_cannot_consume_analytics(self):
        with self.assertRaises(ValueError):
            preview_schedule(ledger=FakeLedger(),token='owner',
                tenant_id='shop',intent_id='id',mode='manual',
                timezone_name='America/New_York',
                manual_local='2026-11-11T10:00',observations=[],now=100)

if __name__=='__main__':unittest.main()
