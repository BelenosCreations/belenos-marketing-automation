import sqlite3
import unittest
from creator_identities import CreatorIdentityPolicy

class CreatorIdentityTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.policy=CreatorIdentityPolicy(self.db)
        self.policy.set_status(tenant_id='belenos',platform='facebook',account_id='maker-1',status='approved',reason='industry educator')
        self.policy.set_status(tenant_id='busy_b',platform='facebook',account_id='maker-1',status='blocked',reason='not relevant')

    def screen(self,tenant='belenos',platform='facebook',account='maker-1',verified=True):
        return self.policy.screen(tenant_id=tenant,platform=platform,account_id=account,identity_verified=verified)

    def test_approved_business_creator(self):
        self.assertEqual(self.screen()[0],'eligible')

    def test_same_creator_blocked_other_business(self):
        self.assertEqual(self.screen(tenant='busy_b')[0],'blocked')

    def test_unknown_creator_held(self):
        self.assertEqual(self.screen(account='unknown')[0],'approval_required')

    def test_unverified_identity_held_even_if_approved(self):
        self.assertEqual(self.screen(verified=False)[0],'approval_required')

    def test_same_name_other_platform_not_approved(self):
        self.assertEqual(self.screen(platform='instagram')[0],'approval_required')

    def test_competitor_exclusion_overrides_prior_approval(self):
        self.policy.set_status(tenant_id='belenos',platform='facebook',account_id='maker-1',status='blocked',reason='local competitor')
        self.assertEqual(self.screen()[0],'blocked')

    def test_review_status_holds_content(self):
        self.policy.set_status(tenant_id='belenos',platform='facebook',account_id='maker-1',status='review',reason='check local competition')
        self.assertEqual(self.screen()[0],'approval_required')

    def test_invalid_platform_denied(self):
        self.assertEqual(self.screen(platform='unknown-platform')[0],'blocked')

    def test_empty_identity_denied(self):
        self.assertEqual(self.screen(account='')[0],'blocked')

    def test_invalid_status_rejected(self):
        with self.assertRaises(ValueError):
            self.policy.set_status(tenant_id='belenos',platform='facebook',account_id='x',status='published',reason='bad')

    def test_shared_social_domain_not_globally_blocked(self):
        self.policy.set_status(tenant_id='belenos',platform='facebook',account_id='competitor-1',status='blocked',reason='local competitor')
        self.policy.set_status(tenant_id='belenos',platform='facebook',account_id='educator-2',status='approved',reason='noncompeting creator')
        self.assertEqual(self.screen(account='competitor-1')[0],'blocked')
        self.assertEqual(self.screen(account='educator-2')[0],'eligible')

    def test_tenant_separation(self):
        self.assertEqual(self.screen(tenant='other')[0],'approval_required')

if __name__=='__main__':
    unittest.main()
