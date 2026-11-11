import unittest
from schedule_readiness import assess_schedule_readiness

class FakeLedger:
    def __init__(self, **changes):
        self.state=dict(intent_id='id',request_id='req',active=True,
            draft_unchanged=True,content_complete=True,
            content_unchanged=True,attachments_verified=True)
        self.state.update(changes)
    def inspect(self,*,token,tenant_id,intent_id,now):
        if token!='owner' or tenant_id!='shop':
            raise PermissionError('Denied')
        if intent_id!='id':
            raise KeyError('Not found')
        return self.state

class ScheduleReadinessTests(unittest.TestCase):
    def check(self,ledger=None,**kwargs):
        params=dict(ledger=ledger or FakeLedger(),token='owner',tenant_id='shop',
                    intent_id='id',proposed_at=200,now=100)
        params.update(kwargs)
        return assess_schedule_readiness(**params)

    def test_healthy_intent_still_cannot_schedule(self):
        result=self.check()
        self.assertFalse(result['ready_to_schedule'])
        self.assertFalse(result['publishing_enabled'])
        self.assertIn('final_approval_not_implemented',result['blockers'])

    def test_revoked_intent_held(self):
        self.assertIn('approval_intent_revoked',
            self.check(FakeLedger(active=False))['blockers'])

    def test_changed_media_held(self):
        self.assertIn('supporting_content_changed',
            self.check(FakeLedger(content_unchanged=False))['blockers'])

    def test_unverified_attachment_held(self):
        self.assertIn('attachments_unverified',
            self.check(FakeLedger(attachments_verified=False))['blockers'])

    def test_past_time_held(self):
        self.assertIn('scheduled_time_not_future',
            self.check(proposed_at=99)['blockers'])

    def test_cross_tenant_denied(self):
        with self.assertRaises(PermissionError):
            self.check(tenant_id='other')

    def test_invalid_timestamp_denied(self):
        with self.assertRaises(ValueError):
            self.check(proposed_at=True)

if __name__=='__main__':unittest.main()
