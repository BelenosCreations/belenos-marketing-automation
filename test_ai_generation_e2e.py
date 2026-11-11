"""End-to-end offline test: confirmed facts -> quota -> OpenAI envelope -> held draft."""
import json
import sqlite3
import unittest
from decimal import Decimal
from ai_cost_ledger import AICostLedger,AITokenPricing
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from ai_account_policy import AIPolicyStore
from ai_business_facts import AIBusinessFacts
from ai_draft_request import AIDraftRequestBuilder
from ai_content_plan import AIContentPlan
from ai_content_drafts import AIContentDraftStore
from ai_sponsorship import SponsoredAIQuota,SponsorshipPlan
from ai_generation_workflow import AIDraftGenerationWorkflow
from openai_responses_executor import OpenAIResponsesExecutor

class EndToEndAIGenerationTests(unittest.TestCase):
    def test_confirmed_facts_to_unpublished_draft_without_network(self):
        db=sqlite3.connect(':memory:')
        directory=AccountDirectory(db)
        directory.bootstrap_owner('shop','owner')
        sessions=SessionStore(db)
        token=sessions.issue(Principal('owner','shop',Role.OWNER),now=100)
        policy=AIPolicyStore(db=db,sessions=sessions,directory=directory)
        facts=AIBusinessFacts(db=db,policy_store=policy)
        facts.confirm(token=token,now=101,
            facts={'business_name':'Example Shop',
                   'products':'Personalized tumblers'})
        captured=[]
        def fake_transport(payload):
            captured.append(payload)
            return {'status':'completed','error':None,'incomplete_details':None,
                'usage':{'input_tokens':1000,'output_tokens':200},
                'output':[{'type':'message','role':'assistant',
                    'status':'completed','content':[{'type':'output_text',
                    'text':json.dumps({
                        'post_text':'Explore personalized tumblers at Example Shop.',
                        'image_prompt':'Product photograph of a plain tumbler'})
                    }]}]}
        drafts=AIContentDraftStore(db=db,policy_store=policy)
        ledger=AICostLedger(db)
        pricing=AITokenPricing(Decimal('1.00'),Decimal('4.00'))
        workflow=AIDraftGenerationWorkflow(
            plan=AIContentPlan(request_builder=AIDraftRequestBuilder(
                policy_store=policy)),facts=facts,
            quota=SponsoredAIQuota(db=db,policy_store=policy),drafts=drafts,
            executor=OpenAIResponsesExecutor(transport=fake_transport,
                usage_observer=lambda **usage:ledger.record_trusted(
                    **usage,pricing=pricing,now=102)))
        result=workflow.generate_sponsored(
            token=token,now=102,topic='Tumblers',platform='facebook',
            month='2026-11',
            sponsorship_plan=SponsorshipPlan('owner',1,500),
            needs_media=True)
        self.assertTrue(result['created'])
        self.assertEqual(result['draft']['status'],'needs_media')
        self.assertFalse(result['draft']['publishing_enabled'])
        self.assertEqual(result['draft']['revision'],1)
        self.assertEqual(result['fact_revision'],1)
        self.assertEqual(len(captured),1)
        summary=ledger.summary_trusted(tenant_id='shop',subject_id='owner')
        self.assertEqual(summary['events'],1)
        self.assertEqual(summary['estimated_micro_usd'],1800)
        self.assertFalse(summary['actual_billing_verified'])
        self.assertIs(captured[0]['store'],False)
        self.assertEqual(captured[0]['tools'],[])
        self.assertEqual(len(drafts.list_mine(
            token=token,now=103)['drafts']),1)

if __name__=='__main__':
    unittest.main()
