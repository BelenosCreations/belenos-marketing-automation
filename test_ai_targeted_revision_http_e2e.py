"""In-memory, zero-network end-to-end tests of targeted OpenAI revision WSGI."""
import io
import json
import sqlite3
import unittest
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from ai_account_policy import AIPolicyStore
from ai_business_facts import AIBusinessFacts
from ai_content_drafts import AIContentDraftStore
from ai_content_plan import AIContentPlan
from ai_draft_request import AIDraftRequestBuilder
from ai_sponsorship import SponsoredAIQuota,SponsorshipPlan
from ai_generation_idempotency import AIGenerationIdempotency
from ai_targeted_revision_workflow import AITargetedRevisionWorkflow
from bam_ai_revision_wsgi import BAMAIRevisionWSGI
from content_attachments import AttachmentRegistry

NOW=1794355200

class RevisionHTTPE2ETests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        directory=AccountDirectory(self.db)
        directory.bootstrap_owner('shop','owner')
        directory.bootstrap_owner('other','another')
        sessions=SessionStore(self.db)
        self.owner=sessions.issue(Principal('owner','shop',Role.OWNER),
                                  now=NOW-10)
        self.other=sessions.issue(Principal('another','other',Role.OWNER),
                                  now=NOW-10)
        policy=AIPolicyStore(db=self.db,sessions=sessions,directory=directory)
        facts=AIBusinessFacts(db=self.db,policy_store=policy)
        facts.confirm(token=self.owner,now=NOW-9,
            facts={'business_name':'Example Shop','product':'Custom tumblers'})
        self.drafts=AIContentDraftStore(db=self.db,policy_store=policy)
        original=self.drafts.stage(token=self.owner,now=NOW-8,
            platform='facebook',
            response={'post_text':'Original factual copy',
                      'image_prompt':'Neutral tumbler illustration'},
            include_image_prompt=True,needs_media=True)
        self.rid=original['draft_id']
        self.calls=[]
        def execute(*,request,max_output_tokens):
            self.calls.append((request,max_output_tokens))
            target=json.loads(request['input_json'])['revision_target']
            return {'revised_text':(
                'Revised factual post copy' if target=='post_text'
                else 'Original generic illustration with beige background')}
        workflow=AITargetedRevisionWorkflow(
            plan=AIContentPlan(request_builder=AIDraftRequestBuilder(
                policy_store=policy)),facts=facts,
            quota=SponsoredAIQuota(db=self.db,policy_store=policy),
            drafts=self.drafts,executor=execute,
            idempotency=AIGenerationIdempotency(
                db=self.db,policy_store=policy))
        self.workflow=workflow
        self.app=BAMAIRevisionWSGI(workflow=workflow,enabled=True,
            plan_resolver=lambda **kwargs:SponsorshipPlan(
                'owner',monthly_requests=4,max_output_tokens=500),
            clock=lambda:NOW)

    def send(self,*,token=None,key=None,body=None):
        if body is None:
            body={'draft_id':self.rid,'expected_revision':1,
                  'target':'post_text','instruction':'Make it concise',
                  'topic':'Tumblers'}
        raw=json.dumps(body).encode('utf-8')
        env={'wsgi.url_scheme':'https','PATH_INFO':'/api/v1/ai/targeted-revision',
             'REQUEST_METHOD':'POST','CONTENT_TYPE':'application/json',
             'CONTENT_LENGTH':str(len(raw)),'wsgi.input':io.BytesIO(raw),
             'HTTP_AUTHORIZATION':'Bearer '+(token or self.owner),
             'HTTP_IDEMPOTENCY_KEY':key or 'a'*32}
        captured=[]
        response=b''.join(self.app(env,lambda status,headers:
            captured.append(status)))
        return captured[0],json.loads(response)

    def test_copy_then_image_revision_still_pending_review(self):
        code,saved=self.send()
        self.assertEqual(code,'201 Created')
        self.assertEqual(saved['revision'],2)
        self.assertFalse(saved['publishing_enabled'])
        self.assertEqual(self.calls[0][1],500)
        current=self.drafts.get(token=self.owner,now=NOW,draft_id=self.rid)
        self.assertEqual(current['post_text'],'Revised factual post copy')
        self.assertEqual(current['image_prompt'],
                         'Neutral tumbler illustration')
        self.assertEqual(current['status'],'needs_media')
        self.assertEqual(self.send()[0],'409 Conflict')
        self.assertEqual(len(self.calls),1)
        attachments=AttachmentRegistry(self.db)
        attachment=attachments.register_pending(
            tenant_id='shop',request_id=self.rid,item='image',
            media_type='image/png',sha256='a'*64,
            storage_key='private/test-image',now=NOW)
        attachments.validate_trusted(tenant_id='shop',
            attachment_id=attachment,approved=True)
        verified=self.drafts.attach_verified_media(
            token=self.owner,now=NOW,draft_id=self.rid,
            attachment_id=attachment,attachments=attachments)
        self.assertTrue(verified['media_attached'])
        code,revised=self.send(key='b'*32,body={
            'draft_id':self.rid,'expected_revision':2,
            'target':'image_prompt','instruction':'Change background only',
            'topic':'Tumblers'})
        self.assertEqual(code,'201 Created')
        self.assertEqual(revised['revision'],3)
        again=self.drafts.get(token=self.owner,now=NOW,draft_id=self.rid)
        self.assertEqual(again['post_text'],'Revised factual post copy')
        self.assertIn('beige background',again['image_prompt'])
        self.assertFalse(again['media_attached'])
        self.assertEqual(again['status'],'needs_media')
        self.assertFalse(again['publishing_enabled'])
        self.assertEqual(len(self.calls),2)
        self.assertEqual(self.db.execute(
            "SELECT accepted FROM bam_ai_usage WHERE tenant_id='shop'"
        ).fetchone()[0],2)

    def test_cross_tenant_and_untrusted_plan_claims_rejected(self):
        code,body=self.send(token=self.other)
        self.assertEqual(code,'404 Not Found')
        self.assertNotIn('Original factual copy',str(body))
        code,body=self.send(body={
            'draft_id':self.rid,'expected_revision':1,'target':'post_text',
            'instruction':'Make concise','topic':'Tumblers',
            'model':'unapproved-paid-provider'})
        self.assertEqual(code,'400 Bad Request')
        self.assertEqual(self.calls,[])
        self.assertIsNone(self.db.execute(
            'SELECT accepted FROM bam_ai_usage LIMIT 1').fetchone())

    def test_ambiguous_provider_text_remains_unpublished(self):
        calls=self.calls
        def invalid(**kwargs):
            calls.append(kwargs)
            return '{"revised_text":"One","revised_text":"Two"}'
        self.workflow.executor=invalid
        code,response=self.send()
        self.assertEqual(code,'422 Unprocessable Entity')
        self.assertNotIn('revised_text',str(response))
        draft=self.drafts.get(token=self.owner,now=NOW,draft_id=self.rid)
        self.assertEqual(draft['revision'],1)
        self.assertEqual(draft['post_text'],'Original factual copy')
        code,replay=self.send()
        self.assertEqual(code,'200 OK')
        self.assertEqual(replay['reason'],'already_failed')
        self.assertEqual(len(calls),1)

if __name__=='__main__':
    unittest.main()
