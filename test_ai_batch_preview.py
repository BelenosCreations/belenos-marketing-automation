"""Advance AI campaign topic plan only: no provider, billing or post writes."""
import sqlite3
import unittest
from accounts import AccountDirectory
from access_policy import Principal,Role
from sessions import SessionStore
from ai_account_policy import AIPolicyStore
from ai_business_facts import AIBusinessFacts
from ai_draft_request import AIDraftRequestBuilder
from ai_content_plan import AIContentPlan
from ai_batch_preview import AIBatchPreview


class AIBatchPreviewTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        directory=AccountDirectory(self.db)
        directory.bootstrap_owner('shop','owner')
        directory.bootstrap_owner('other','other')
        directory.set_member(Principal('owner','shop',Role.OWNER),
                             'creator',Role.CONTENT_CREATOR)
        sessions=SessionStore(self.db)
        self.owner=sessions.issue(Principal('owner','shop',Role.OWNER),now=100)
        self.other=sessions.issue(Principal('other','other',Role.OWNER),now=100)
        self.creator=sessions.issue(Principal('creator','shop',Role.CONTENT_CREATOR),now=100)
        policy=AIPolicyStore(db=self.db,sessions=sessions,directory=directory)
        self.policy=policy
        self.facts=AIBusinessFacts(db=self.db,policy_store=policy)
        self.plan=AIBatchPreview(
            plan=AIContentPlan(request_builder=AIDraftRequestBuilder(
                policy_store=policy)),facts=self.facts)
    def run_preview(self,**changes):
        kwargs=dict(token=self.owner,now=102,topics=[
            'Tumbler highlight','Customer gift idea'],
            platform='facebook',include_image_prompt=True)
        kwargs.update(changes)
        return self.plan.preview(**kwargs)

    def test_requires_confirmed_facts_and_never_calls_provider(self):
        with self.assertRaises(ValueError):
            self.run_preview()
        self.facts.confirm(token=self.owner,now=101,
            facts={'business_name':'Example Creations',
                   'product':'Custom tumblers'})
        result=self.run_preview()
        self.assertEqual(result['tenant_id'],'shop')
        self.assertEqual(result['fact_revision'],1)
        self.assertEqual(result['mode'],'bam_sponsored')
        self.assertEqual(result['status'],'planning_only')
        self.assertEqual(result['planned_individual_requests'],2)
        self.assertEqual(result['provider_requests_made'],0)
        self.assertEqual(result['drafts_created'],0)
        self.assertIs(result['quota_reserved'],False)
        self.assertIs(result['actual_cost_known'],False)
        self.assertFalse(result['publishing_enabled'])
        self.assertEqual(result['items'][0],{
            'topic':'Tumbler highlight','platform':'facebook',
            'image_prompt_planned':True})
        self.assertEqual(self.db.execute(
            'SELECT COUNT(*) FROM bam_ai_usage').fetchone()[0],0)

    def test_current_user_memory_and_business_scope(self):
        self.facts.confirm(token=self.owner,now=101,
            facts={'business_name':'Example Creations'})
        self.policy.replace_memory(token=self.owner,now=101,
            memory={'tone':'short Facebook posts'})
        result=self.run_preview()
        self.assertEqual(result['mode'],'bam_sponsored')
        self.assertNotIn('short Facebook posts',str(result))
        creator=self.run_preview(token=self.creator)
        self.assertEqual(creator['tenant_id'],'shop')
        self.assertNotIn('short Facebook posts',str(creator))
        with self.assertRaises(ValueError):
            self.run_preview(token=self.other)
        self.facts.confirm(token=self.other,now=101,
            facts={'business_name':'Different Shop'})
        other=self.run_preview(token=self.other)
        self.assertEqual(other['tenant_id'],'other')
        self.assertNotIn('Example Creations',str(other))

    def test_personal_key_mode_does_not_claim_paid_usage(self):
        self.facts.confirm(token=self.owner,now=101,
            facts={'business_name':'Example Creations'})
        self.policy.set_mode(token=self.owner,now=101,
            mode='own_openai_key',credential_ref='vault:abcdefghijklmnop')
        result=self.run_preview(include_image_prompt=False)
        self.assertEqual(result['mode'],'own_openai_key')
        self.assertFalse(result['items'][0]['image_prompt_planned'])
        self.assertEqual(result['provider_requests_made'],0)
        self.assertNotIn('vault:',str(result))

    def test_invalid_duplicate_or_untrusted_topics_fail_before_planning(self):
        self.facts.confirm(token=self.owner,now=101,
            facts={'business_name':'Example Creations'})
        for bad in ([],['a']*15,['Same','same'],[' a'],['a '],
                    [{'topic':'a'}],[''],['x'*301]):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                self.run_preview(topics=bad)
        for bad in (None,1,'yes'):
            with self.assertRaises(ValueError):
                self.run_preview(include_image_prompt=bad)
        with self.assertRaises(ValueError):
            self.run_preview(platform='not-a-platform')
        self.assertEqual(self.db.execute(
            'SELECT COUNT(*) FROM bam_ai_usage').fetchone()[0],0)

if __name__=='__main__':
    unittest.main()
