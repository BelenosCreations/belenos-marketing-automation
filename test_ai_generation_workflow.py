import sqlite3
import unittest
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from ai_account_policy import AIPolicyStore
from ai_business_facts import AIBusinessFacts
from ai_content_plan import AIContentPlan
from ai_content_drafts import AIContentDraftStore
from ai_draft_request import AIDraftRequestBuilder
from ai_sponsorship import SponsoredAIQuota,SponsorshipPlan
from ai_generation_workflow import AIDraftGenerationWorkflow

class GenerationWorkflowTests(unittest.TestCase):
    def setUp(self):
        db=sqlite3.connect(':memory:')
        directory=AccountDirectory(db)
        directory.bootstrap_owner('shop','owner')
        sessions=SessionStore(db)
        self.token=sessions.issue(Principal('owner','shop',Role.OWNER),now=100)
        policy=AIPolicyStore(db=db,sessions=sessions,directory=directory)
        self.policy=policy
        self.facts=AIBusinessFacts(db=db,policy_store=policy)
        self.quota=SponsoredAIQuota(db=db,policy_store=policy)
        self.drafts=AIContentDraftStore(db=db,policy_store=policy)
        self.calls=[]
        def executor(*,request,max_output_tokens):
            self.calls.append((request,max_output_tokens))
            return {'post_text':'Custom tumblers from Example Shop.',
                    'image_prompt':'Neutral photo of a tumbler'}
        self.workflow=AIDraftGenerationWorkflow(
            plan=AIContentPlan(request_builder=AIDraftRequestBuilder(
                policy_store=policy)),facts=self.facts,quota=self.quota,
            drafts=self.drafts,executor=executor)
        self.plan=SponsorshipPlan('owner',monthly_requests=1,
                                  max_output_tokens=500)

    def generate(self,**changes):
        kwargs=dict(token=self.token,now=102,topic='Tumblers',
                    platform='facebook',month='2026-11',
                    sponsorship_plan=self.plan,
                    include_image_prompt=True,needs_media=True)
        kwargs.update(changes)
        return self.workflow.generate_sponsored(**kwargs)

    def test_facts_missing_never_spend_or_call_executor(self):
        with self.assertRaises(ValueError):
            self.generate()
        self.assertEqual(self.calls,[])
        self.facts.confirm(token=self.token,now=101,
            facts={'business_name':'Example Shop','product':'Custom tumblers'})
        generated=self.generate()
        self.assertTrue(generated['created'])
        self.assertEqual(generated['fact_revision'],1)
        self.assertEqual(generated['remaining_sponsored_requests'],0)
        self.assertEqual(generated['draft']['status'],'needs_media')
        self.assertFalse(generated['publishing_enabled'])
        self.assertEqual(self.calls[0][1],500)
        self.assertEqual(self.generate()['reason'],'limit_reached')
        self.assertEqual(len(self.calls),1)

    def test_personal_key_requires_separate_vault_path(self):
        self.facts.confirm(token=self.token,now=101,
            facts={'business_name':'Example Shop'})
        self.policy.set_mode(token=self.token,now=101,
            mode='own_openai_key',credential_ref='vault:abcdefghijklmnop')
        with self.assertRaises(ValueError):
            self.generate()
        self.assertEqual(self.calls,[])

    def test_invalid_executor_response_is_not_staged(self):
        self.facts.confirm(token=self.token,now=101,
            facts={'business_name':'Example Shop'})
        self.workflow.executor=lambda **kwargs:{
            'post_text':'Hi','image_prompt':None,'published':True}
        with self.assertRaises(ValueError):
            self.generate()
        self.assertEqual(self.drafts.list_mine(
            token=self.token,now=103)['drafts'],[])
        self.assertEqual(self.generate()['reason'],'limit_reached')

if __name__=='__main__':
    unittest.main()
