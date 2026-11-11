import unittest
from schedule_preview import preview_schedule
from test_schedule_readiness import FakeLedger

class SchedulePreviewTests(unittest.TestCase):
    def preview(self,**kwargs):
        params=dict(ledger=FakeLedger(),token='owner',tenant_id='shop',
                    intent_id='id',mode='manual',timezone_name='America/New_York',
                    manual_local='2026-11-11T10:00',now=100)
        params.update(kwargs)
        return preview_schedule(**params)

    def test_manual_preview_never_schedules(self):
        result=self.preview()
        self.assertEqual(result['status'],'held')
        self.assertFalse(result['scheduled_job_created'])
        self.assertFalse(result['readiness']['ready_to_schedule'])

    def test_smart_candidates_are_preview_only(self):
        result=self.preview(mode='smart',manual_local=None,
            smart_candidates=['2026-11-12T18:30','2026-11-11T10:00'])
        self.assertEqual(result['candidate_count'],2)
        self.assertEqual(result['selection_policy'],'earliest_candidate_only')
        self.assertFalse(result['publishing_enabled'])

    def test_spring_forward_gap_rejected(self):
        with self.assertRaises(ValueError):
            self.preview(manual_local='2026-03-08T02:30')

    def test_fall_back_ambiguity_rejected(self):
        with self.assertRaises(ValueError):
            self.preview(manual_local='2026-11-01T01:30')

    def test_cross_tenant_denied(self):
        with self.assertRaises(PermissionError):
            self.preview(tenant_id='other')

    def test_bad_timezone_rejected(self):
        with self.assertRaises(ValueError):
            self.preview(timezone_name='Not/A_Zone')

    def test_mixed_mode_rejected(self):
        with self.assertRaises(ValueError):
            self.preview(mode='smart',smart_candidates=['2026-11-11T10:00'])

    def test_duplicate_candidates_rejected(self):
        with self.assertRaises(ValueError):
            self.preview(mode='smart',manual_local=None,
                smart_candidates=['2026-11-11T10:00','2026-11-11T10:00'])

if __name__=='__main__':unittest.main()
