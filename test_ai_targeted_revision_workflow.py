"""Offline targeted revision: no network, no media/approval bypass."""
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
from ai_targeted_revision_workflow import AITargetedRevisionWorkflow


class TargetedRevisionTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        directory=AccountDirectory(self.db)
        directory.bootstrap_owner('shop','owner')
        directory.set_member(Principal('owner','shop',Role.OWNER),
                             'creator',Role.CONTENT_CREATOR)
        directory.bootstrap_owner('other','other_owner')
        sessions=SessionStore(self.db)
        self.token=sessions.issue(Principal('owner','shop',Role.OWNER),now=100)
        self.creator=sessions.issue(Principal('creator','shop',Role.CONTENT_CREATOR),now=100)
        self.other=sessions.issue(Principal('other_owner','other',Role.OWNER),now=100)
        self.policy=AIPolicyStore(db=self.db,sessions=sessions,directory=directory)
        self.facts=AIBusinessFacts(db=self.db,policy_store=self.policy)
        self.facts.confirm(token=self.token,now=101,
                           facts={'business_name':'Example Shop',
                                  'product':'Custom tumblers'})
        self.quota=SponsoredAIQuota(db=self.db,policy_store=self.policy)
        self.drafts=AIContentDraftStore(db=self.db,policy_store=self.policy)
        self.draft=self.drafts.stage(token=self.token,now=101,
            platform='facebook',
            response={'post_text':'First post',
                      'image_prompt':'A simple tumbler on neutral background'},
            include_image_prompt=True,needs_media=True)
        self.calls=[]
        def executor(*,request,max_output_tokens):
            self.calls.append((request,max_output_tokens))
            return {'revised_text':'A revised post'}
        self.dedup=AIGenerationIdempotency(db=self.db,policy_store=self.policy)
        self.workflow=AITargetedRevisionWorkflow(
            plan=AIContentPlan(request_builder=AIDraftRequestBuilder(
                policy_store=self.policy)),facts=self.facts,
            quota=self.quota,drafts=self.drafts,
            executor=executor,idempotency=self.dedup)
        self.plan=SponsorshipPlan('owner',monthly_requests=3,
                                  max_output_tokens=200)

    def revise(self,**changes):
        opts=dict(token=self.token,now=102,draft_id=self.draft['draft_id'],
            expected_revision=1,target='post_text',instruction='Shorten it',
            topic='Tumblers',month='2026-11',
            sponsorship_plan=self.plan,request_key='a'*32)
        opts.update(changes)
        return self.workflow.revise_sponsored(**opts)

    def test_one_component_only_replay_does_not_charge_again(self):
        first=self.revise()
        self.assertTrue(first['revised'])
        self.assertEqual(first['draft']['post_text'],'A revised post')
        self.assertEqual(first['draft']['image_prompt'],
                         'A simple tumbler on neutral background')
        self.assertEqual(first['draft']['revision'],2)
        self.assertEqual(first['draft']['status'],'needs_media')
        self.assertFalse(first['draft']['publishing_enabled'])
        self.assertEqual(first['remaining_sponsored_requests'],2)
        self.assertEqual(len(self.calls),1)
        request=self.calls[0][0]
        self.assertEqual(request['response_schema'],{'revised_text':'string'})
        self.assertEqual(self.calls[0][1],200)
        # Once revision advances, callers must refresh; no second paid call.
        with self.assertRaises(ValueError):
            self.revise()
        self.assertEqual(len(self.calls),1)
        self.assertEqual(self.db.execute(
            "SELECT accepted FROM bam_ai_usage WHERE tenant_id='shop'"
        ).fetchone()[0],1)

    def test_image_only_revision_invalidates_verified_media(self):
        from content_attachments import AttachmentRegistry
        attachments=AttachmentRegistry(self.db)
        attachment=attachments.register_pending(
            tenant_id='shop',request_id=self.draft['draft_id'],item='image',
            media_type='image/png',sha256='a'*64,storage_key='private/image',
            now=101)
        attachments.validate_trusted(tenant_id='shop',
            attachment_id=attachment,approved=True)
        self.drafts.attach_verified_media(
            token=self.token,now=101,draft_id=self.draft['draft_id'],
            attachment_id=attachment,attachments=attachments)
        self.workflow.executor=lambda **kwargs:{'revised_text':'New neutral backdrop'}
        result=self.revise(target='image_prompt',instruction='Simplify image',
                           request_key='b'*32)
        updated=result['draft']
        self.assertEqual(updated['post_text'],'First post')
        self.assertEqual(updated['image_prompt'],'New neutral backdrop')
        self.assertFalse(updated['media_attached'])
        self.assertEqual(updated['status'],'needs_media')
        self.assertFalse(updated['publishing_enabled'])

    def test_stale_and_cross_subject_fail_before_quota_or_provider(self):
        with self.assertRaises(LookupError):
            self.revise(token=self.creator)
        with self.assertRaises(LookupError):
            self.revise(token=self.other)
        with self.assertRaises(ValueError):
            self.revise(expected_revision=99)
        with self.assertRaises(ValueError):
            self.revise(target='not_a_component')
        with self.assertRaises(ValueError):
            self.revise(request_key=None)
        self.assertEqual(self.calls,[])
        self.assertIsNone(self.db.execute(
            'SELECT accepted FROM bam_ai_usage LIMIT 1').fetchone())

    def test_personal_key_never_consumes_sponsored_quota(self):
        self.policy.set_mode(token=self.token,now=101,
            mode='own_openai_key',
            credential_ref='vault:abcdefghijklmnop')
        with self.assertRaises(ValueError):
            self.revise()
        self.assertEqual(self.calls,[])
        self.assertIsNone(self.db.execute(
            'SELECT accepted FROM bam_ai_usage LIMIT 1').fetchone())

    def test_provider_forged_claims_fail_and_retry_is_held(self):
        self.workflow.executor=lambda **kwargs:(
            self.calls.append(kwargs) or
            {'revised_text':'Draft','publish_now':True})
        with self.assertRaises(ValueError):
            self.revise()
        status=self.dedup.status(token=self.token,now=103,request_key='a'*32)
        self.assertEqual(status['status'],'failed')
        current=self.drafts.get(token=self.token,now=103,
                                draft_id=self.draft['draft_id'])
        self.assertEqual(current['revision'],1)
        self.assertEqual(current['post_text'],'First post')
        retry=self.revise()
        self.assertFalse(retry['revised'])
        self.assertEqual(retry['reason'],'already_failed')
        self.assertEqual(len(self.calls),1)
        self.assertEqual(self.db.execute(
            "SELECT accepted FROM bam_ai_usage WHERE tenant_id='shop'"
        ).fetchone()[0],1)

    def test_stale_draft_created_during_executor_rejected(self):
        def mutate(**kwargs):
            self.drafts.revise(token=self.token,now=102,
                draft_id=self.draft['draft_id'],target='post_text',
                revised_text='Someone changed it',expected_revision=1)
            return {'revised_text':'Stale AI draft'}
        self.workflow.executor=mutate
        with self.assertRaises(ValueError):
            self.revise()
        updated=self.drafts.get(token=self.token,now=103,
                                draft_id=self.draft['draft_id'])
        self.assertEqual(updated['post_text'],'Someone changed it')
        self.assertEqual(updated['revision'],2)
        self.assertEqual(self.dedup.status(
            token=self.token,now=103,request_key='a'*32)['status'],'failed')

    def test_fact_change_during_provider_call_fails_closed(self):
        def change(**kwargs):
            self.facts.confirm(token=self.token,now=102,
                facts={'business_name':'Updated Shop'},
                expected_revision=1)
            return {'revised_text':'Old incorrect claim'}
        self.workflow.executor=change
        with self.assertRaises(ValueError):
            self.revise()
        self.assertEqual(self.drafts.get(token=self.token,now=103,
            draft_id=self.draft['draft_id'])['revision'],1)

    def test_quota_denied_no_executor_and_key_held(self):
        zero=SponsorshipPlan('owner',monthly_requests=0,
                             max_output_tokens=100)
        rejected=self.revise(sponsorship_plan=zero)
        self.assertEqual(rejected['reason'],'not_entitled')
        self.assertFalse(rejected['publishing_enabled'])
        self.assertFalse(rejected['revised'])
        self.assertEqual(self.calls,[])
        self.assertEqual(self.dedup.status(
            token=self.token,now=103,request_key='a'*32)['status'],'failed')

    def test_replay_completed_key_with_same_draft_revision_cannot_regenerate(self):
        first=self.revise()
        self.assertTrue(first['revised'])
        # Replayed requests are explicitly blocked by the stale revision
        # check, rather than returning a misleading current revision.
        with self.assertRaises(ValueError):
            self.revise()
        self.assertEqual(len(self.calls),1)
        with self.assertRaises(ValueError):
            self.revise(expected_revision=2,instruction='New instruction')

if __name__=='__main__':
    unittest.main()
