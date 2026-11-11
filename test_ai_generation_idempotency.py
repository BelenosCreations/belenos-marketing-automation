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
from ai_generation_idempotency import AIGenerationIdempotency
from ai_generation_workflow import AIDraftGenerationWorkflow

class IdempotentGenerationTests(unittest.TestCase):
    def setUp(self):
        db=sqlite3.connect(':memory:')
        directory=AccountDirectory(db)
        directory.bootstrap_owner('shop','owner')
        directory.bootstrap_owner('other','other')
        directory.set_member(Principal('owner','shop',Role.OWNER),
                             'coworker',Role.CONTENT_CREATOR)
        sessions=SessionStore(db)
        self.token=sessions.issue(Principal('owner','shop',Role.OWNER),now=100)
        self.other=sessions.issue(Principal('other','other',Role.OWNER),now=100)
        self.coworker=sessions.issue(Principal('coworker','shop',
                                             Role.CONTENT_CREATOR),now=100)
        policy=AIPolicyStore(db=db,sessions=sessions,directory=directory)
        self.facts=AIBusinessFacts(db=db,policy_store=policy)
        self.facts.confirm(token=self.token,now=101,
            facts={'business_name':'Example Shop'})
        self.facts.confirm(token=self.other,now=101,
            facts={'business_name':'Other Shop'})
        self.calls=[]
        def executor(**kwargs):
            self.calls.append(kwargs)
            return {'post_text':'Custom tumblers','image_prompt':None}
        self.drafts=AIContentDraftStore(db=db,policy_store=policy)
        self.dedup=AIGenerationIdempotency(db=db,policy_store=policy)
        self.workflow=AIDraftGenerationWorkflow(
            plan=AIContentPlan(request_builder=AIDraftRequestBuilder(
                policy_store=policy)),facts=self.facts,
            quota=SponsoredAIQuota(db=db,policy_store=policy),
            drafts=self.drafts,executor=executor,idempotency=self.dedup)
        self.plan=SponsorshipPlan('owner',2,300)
        self.key='a'*32

    def run_generation(self,**kwargs):
        args=dict(token=self.token,now=102,topic='Tumblers',
            platform='facebook',month='2026-11',
            sponsorship_plan=self.plan,
            include_image_prompt=False,needs_media=False,
            request_key=self.key)
        args.update(kwargs)
        return self.workflow.generate_sponsored(**args)

    def test_missing_request_key_denied_before_quota(self):
        with self.assertRaises(ValueError):
            self.run_generation(request_key=None)
        self.assertEqual(self.calls,[])

    def test_replay_does_not_repeat_call_or_quota(self):
        first=self.run_generation()
        second=self.run_generation()
        self.assertTrue(first['created'])
        self.assertFalse(second['created'])
        self.assertEqual(second['reason'],'already_completed')
        self.assertEqual(len(self.calls),1)
        self.assertEqual(first['remaining_sponsored_requests'],1)
        self.assertEqual(len(self.drafts.list_mine(
            token=self.token,now=103)['drafts']),1)

    def test_request_status_is_private_and_read_only(self):
        missing=self.dedup.status(token=self.token,now=102,
            request_key=self.key)
        self.assertFalse(missing['found'])
        first=self.run_generation()
        completed=self.dedup.status(token=self.token,now=103,
            request_key=self.key)
        self.assertEqual(completed['status'],'completed')
        self.assertEqual(completed['draft_id'],first['draft']['draft_id'])
        other=self.dedup.status(token=self.other,now=103,
            request_key=self.key)
        self.assertFalse(other['found'])
        coworker=self.dedup.status(token=self.coworker,now=103,
            request_key=self.key)
        self.assertFalse(coworker['found'])
        self.assertEqual(len(self.calls),1)

    def test_reused_key_different_payload_rejected(self):
        self.run_generation()
        with self.assertRaises(ValueError):
            self.run_generation(topic='Different')

    def test_failure_does_not_auto_retry(self):
        def failing(**kwargs):
            self.calls.append(kwargs)
            raise RuntimeError('provider failed')
        self.workflow.executor=failing
        with self.assertRaises(RuntimeError):
            self.run_generation()
        second=self.run_generation()
        status=self.dedup.status(token=self.token,now=103,
            request_key=self.key)
        self.assertEqual(status['status'],'failed')
        self.assertIsNone(status['draft_id'])
        self.assertEqual(second['reason'],'already_failed')
        self.assertEqual(len(self.calls),1)

    def test_scope_isolated(self):
        self.assertTrue(self.run_generation()['created'])
        other=self.run_generation(token=self.other)
        self.assertTrue(other['created'])
        self.assertEqual(len(self.calls),2)
        coworker=self.run_generation(token=self.coworker)
        self.assertTrue(coworker['created'])
        self.assertEqual(len(self.calls),3)

if __name__=='__main__':
    unittest.main()
