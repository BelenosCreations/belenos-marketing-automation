"""Read-only tenant posting previews with DST, evidence and limits."""
from datetime import datetime,timezone
import unittest
from posting_time_preview import build_posting_time_preview as preview

def epoch(iso):
    return int(datetime.fromisoformat(iso).timestamp())

def manual(*,zone='America/New_York',times=None):
    return {'tenant_id':'shop','mode':'manual','timezone':zone,
            'manual_times':times or ['10:00','18:30'],
            'configured':True,'publishing_enabled':False}

class PostingTimePreviewTests(unittest.TestCase):
    def test_manual_slots_are_local_time_proposals_not_scheduled_posts(self):
        result=preview(manual(),server_now=epoch('2026-11-11T12:00:00+00:00'))
        self.assertEqual(result['status'],'manual_preview')
        self.assertEqual(result['mode'],'manual')
        self.assertFalse(result['publishing_enabled'])
        self.assertEqual(result['slots'][0],{
            'local_date':'2026-11-11','local_time':'10:00',
            'utc_at':'2026-11-11T15:00:00+00:00'})
        self.assertEqual(len(result['slots']),14)
        self.assertEqual(result['skipped_dst'],0)
        self.assertFalse(result['truncated'])
        self.assertNotIn('scheduled_job_created',result)
        self.assertNotIn('approval',result)
        self.assertTrue(all(slot['utc_at'].endswith('+00:00')
                            for slot in result['slots']))

    def test_spring_gap_is_skipped_not_shifted(self):
        result=preview(manual(times=['02:30','03:30']),
            server_now=epoch('2026-03-08T05:00:00+00:00'),days=2)
        self.assertEqual(result['skipped_dst'],1)
        self.assertNotIn({'local_date':'2026-03-08','local_time':'02:30'},
            [{k:v for k,v in slot.items() if k!='utc_at'}
             for slot in result['slots']])
        self.assertIn('2026-03-08T07:30:00+00:00',
            [x['utc_at'] for x in result['slots']])

    def test_fall_ambiguous_hour_is_skipped(self):
        result=preview(manual(times=['01:30','02:30']),
            server_now=epoch('2026-11-01T04:00:00+00:00'),days=1)
        self.assertEqual(result['skipped_dst'],1)
        self.assertEqual(result['slots'],[{
            'local_date':'2026-11-01','local_time':'02:30',
            'utc_at':'2026-11-01T07:30:00+00:00'}])

    def test_current_and_limits(self):
        result=preview(manual(zone='UTC',times=['08:00','18:00']),
            server_now=epoch('2026-11-11T09:00:00+00:00'),days=2)
        self.assertEqual(result['slots'][0]['utc_at'],
                         '2026-11-11T18:00:00+00:00')
        self.assertEqual(len(result['slots']),3)
        compact=preview(manual(),server_now=epoch('2026-11-11T00:00:00+00:00'),
                        max_slots=3)
        self.assertTrue(compact['truncated'])
        self.assertEqual(len(compact['slots']),3)

    def test_smart_unconfigured_and_invalid_inputs(self):
        smart={'tenant_id':'shop','mode':'smart',
            'timezone':'America/New_York','manual_times':[],
            'configured':True,'publishing_enabled':False}
        result=preview(smart,server_now=epoch('2026-11-11T12:00:00+00:00'))
        self.assertEqual(result['status'],'needs_audience_data')
        self.assertEqual(result['slots'],[])
        unconfigured={**smart,'timezone':None,'configured':False}
        self.assertEqual(preview(unconfigured,server_now=0)['status'],
                         'not_configured')
        for value in (
                {**smart,'publishing_enabled':True},
                {**smart,'manual_times':['10:00']},
                {**smart,'timezone':'Not/A_Zone'},
                {**manual(),'manual_times':[]},
                {**manual(),'manual_times':['10:00','10:00']},
                {**manual(),'manual_times':[True]},
                {**manual(),'manual_times':['24:00']},
                {**manual(),'tenant_id':' '},
                {**smart,'configured':False}):
            with self.subTest(value=value),self.assertRaises(ValueError):
                preview(value,server_now=100)
        for now in (True,-1,'today'):
            with self.assertRaises(ValueError):
                preview(manual(),server_now=now)

if __name__=='__main__':
    unittest.main()
