import json
import sqlite3
import unittest
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from ai_account_policy import AIPolicyStore
from ai_draft_request import AIDraftRequestBuilder
from ai_content_plan import AIContentPlan

class AIContentPlanTests(unittest.TestCase):
    def setUp(self):
        db=sqlite3.connect(':memory:')
        directory=AccountDirectory(db)
        directory.bootstrap_owner('shop','owner')
        sessions=SessionStore(db)
        token=sessions.issue(Principal('owner','shop',Role.OWNER),now=100)
        self.token=token
        self.plan=AIContentPlan(request_builder=AIDraftRequestBuilder(
            policy_store=AIPolicyStore(db=db,sessions=sessions,
                                       directory=directory)))
        self.facts={'business_name':'Example Shop','product':'Custom tumblers'}

    def request(self,**extra):
        args=dict(token=self.token,now=101,verified_facts=self.facts,
                  topic='Product highlight',platform='facebook')
        args.update(extra)
        return self.plan.create_request(**args)

    def test_combined_generation_in_one_request(self):
        request=self.request()
        self.assertEqual(request['provider'],'openai')
        self.assertEqual(request['response_schema'],
                         {'post_text':'string','image_prompt':'string|null'})
        self.assertTrue(json.loads(request['input_json'])['include_image_prompt'])
        self.assertFalse(request['publishing_enabled'])
        draft=self.plan.parse_response(json.dumps({
            'post_text':'Our custom tumblers are here.',
            'image_prompt':'Product photo on neutral background'}),
            include_image_prompt=True)
        self.assertEqual(draft['status'],'draft_pending_verification')
        self.assertFalse(draft['image_created'])

    def test_image_prompt_optional_and_never_claims_image_created(self):
        request=self.request(include_image_prompt=False)
        self.assertFalse(json.loads(request['input_json'])['include_image_prompt'])
        with self.assertRaises(ValueError):
            self.plan.parse_response({'post_text':'Hi','image_prompt':'A picture'},
                                     include_image_prompt=False)
        self.assertIsNone(self.plan.parse_response({
            'post_text':'Hi','image_prompt':None},
            include_image_prompt=False)['image_prompt'])

    def test_targeted_revision_preserves_other_component(self):
        original={'post_text':'Original copy',
                  'image_prompt':'A neutral product photograph'}
        request=self.plan.revision_request(token=self.token,now=101,
            verified_facts=self.facts,topic='Product highlight',
            platform='facebook',current=original,
            target='post_text',instruction='Make it shorter')
        self.assertEqual(json.loads(request['input_json'])['revision_target'],
                         'post_text')
        revised=self.plan.apply_revision(original,target='post_text',
                                         revised_text='Short copy')
        self.assertEqual(revised['image_prompt'],original['image_prompt'])
        self.assertFalse(revised['publishing_enabled'])
        image_revision=self.plan.apply_revision(revised,
            target='image_prompt',revised_text='Blue neutral background')
        self.assertEqual(image_revision['post_text'],'Short copy')
        followup=self.plan.revision_request(token=self.token,now=101,
            verified_facts=self.facts,topic='Product highlight',
            platform='facebook',current=revised,
            target='image_prompt',instruction='Change background')
        self.assertEqual(json.loads(followup['input_json'])['revision_target'],
                         'image_prompt')

    def test_revision_response_is_single_field_only(self):
        self.assertEqual(self.plan.parse_revision_response(
            '{"revised_text":"Short copy"}',target='post_text'),'Short copy')
        for payload in (
            {'revised_text':'Text','published':True},
            {'post_text':'Full draft','image_prompt':None},
            {'revised_text':''},
        ):
            with self.assertRaises(ValueError):
                self.plan.parse_revision_response(payload,target='post_text')
        with self.assertRaises(ValueError):
            self.plan.parse_revision_response('not json',target='image_prompt')

    def test_batch_is_bounded(self):
        args=dict(token=self.token,now=101,verified_facts=self.facts,
                  platform='facebook')
        self.assertEqual(len(self.plan.batch_requests(
            topics=['Product','Store update'],**args)),2)
        with self.assertRaises(ValueError):
            self.plan.batch_requests(topics=['Same','Same'],**args)
        with self.assertRaises(ValueError):
            self.plan.batch_requests(topics=['Topic']*15,**args)
        with self.assertRaises(ValueError):
            self.plan.batch_requests(topics=[{'bad':'topic'}],**args)

    def test_malformed_generation_is_not_approved(self):
        with self.assertRaises(ValueError):
            self.plan.parse_response({'post_text':'Hello',
                'image_prompt':None,'published':True},
                include_image_prompt=True)

if __name__=='__main__':
    unittest.main()
