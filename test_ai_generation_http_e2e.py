"""Offline HTTPS endpoint -> idempotency -> OpenAI envelope -> held draft."""
import io
import json
import sqlite3
import unittest
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from ai_account_policy import AIPolicyStore
from ai_business_facts import AIBusinessFacts
from ai_draft_request import AIDraftRequestBuilder
from ai_content_plan import AIContentPlan
from ai_content_drafts import AIContentDraftStore
from ai_sponsorship import SponsoredAIQuota,SponsorshipPlan
from ai_generation_idempotency import AIGenerationIdempotency
from ai_generation_workflow import AIDraftGenerationWorkflow
from openai_responses_executor import OpenAIResponsesExecutor
from bam_ai_write_wsgi import BAMAIWriteWSGI

class AIHTTPIntegrationTests(unittest.TestCase):
    def test_repeat_request_returns_hold_without_second_provider_call(self):
        now=1794355200
        db=sqlite3.connect(':memory:')
        directory=AccountDirectory(db)
        directory.bootstrap_owner('shop','owner')
        sessions=SessionStore(db)
        token=sessions.issue(Principal('owner','shop',Role.OWNER),now=now-10)
        policy=AIPolicyStore(db=db,sessions=sessions,directory=directory)
        facts=AIBusinessFacts(db=db,policy_store=policy)
        facts.confirm(token=token,now=now-5,
            facts={'business_name':'Example Shop'})
        requests=[]
        def fake_openai(payload):
            requests.append(payload)
            return {'status':'completed','error':None,'incomplete_details':None,
                'output':[{'type':'message','role':'assistant',
                    'status':'completed','content':[{'type':'output_text',
                    'text':json.dumps({'post_text':'Example Shop tumblers',
                        'image_prompt':'A tumbler on a plain background'})}]}]}
        drafts=AIContentDraftStore(db=db,policy_store=policy)
        workflow=AIDraftGenerationWorkflow(
            plan=AIContentPlan(request_builder=AIDraftRequestBuilder(
                policy_store=policy)),facts=facts,
            quota=SponsoredAIQuota(db=db,policy_store=policy),
            drafts=drafts,executor=OpenAIResponsesExecutor(
                transport=fake_openai),
            idempotency=AIGenerationIdempotency(
                db=db,policy_store=policy))
        app=BAMAIWriteWSGI(workflow=workflow,
            plan_resolver=lambda **kwargs:SponsorshipPlan('owner',2,500),
            enabled=True,clock=lambda:now)
        body=json.dumps({'topic':'Tumblers','platform':'facebook',
            'needs_media':True,'include_image_prompt':True}).encode()
        def call():
            env={'wsgi.url_scheme':'https',
                 'PATH_INFO':'/api/v1/ai-generate',
                 'REQUEST_METHOD':'POST',
                 'HTTP_AUTHORIZATION':'Bearer '+token,
                 'HTTP_IDEMPOTENCY_KEY':'a'*32,
                 'CONTENT_TYPE':'application/json',
                 'CONTENT_LENGTH':str(len(body)),
                 'wsgi.input':io.BytesIO(body)}
            statuses=[]
            output=b''.join(app(env,lambda status,headers:
                statuses.append(status)))
            return statuses[0],json.loads(output)
        first_status,first=call()
        second_status,second=call()
        self.assertEqual(first_status,'201 Created')
        self.assertEqual(first['status'],'needs_media')
        self.assertEqual(second_status,'200 OK')
        self.assertEqual(second['reason'],'already_completed')
        self.assertEqual(second['tenant_id'],'shop')
        self.assertEqual(len(requests),1)
        self.assertEqual(len(drafts.list_mine(
            token=token,now=now)['drafts']),1)
        self.assertFalse(first['publishing_enabled'])

if __name__=='__main__':
    unittest.main()
