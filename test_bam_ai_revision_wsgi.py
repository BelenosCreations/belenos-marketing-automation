"""HTTP boundary for AI single-component revisions with injected executor."""
import io
import json
import unittest
from ai_sponsorship import SponsorshipPlan
from bam_ai_revision_wsgi import BAMAIRevisionWSGI

class FakeWorkflow:
    def __init__(self):
        self.calls=[]
        self.problem=None
        self.result='success'
        self.hold_reason='already_in_progress'
    def revise_sponsored(self,**args):
        self.calls.append(args)
        if self.problem:
            raise self.problem
        if self.result=='hold':
            return {'revised':False,'tenant_id':'shop',
                    'reason':self.hold_reason,
                    'publishing_enabled':False}
        return {'revised':True,'tenant_id':'shop',
                'draft':{'tenant_id':'shop','draft_id':args['draft_id'],
                         'revision':args['expected_revision']+1,
                         'status':'needs_media','publishing_enabled':False},
                'publishing_enabled':False}

class WSGIRevisionTests(unittest.TestCase):
    def setUp(self):
        self.workflow=FakeWorkflow()
        self.resolved=[]
        def resolve(**kwargs):
            self.resolved.append(kwargs)
            return SponsorshipPlan('owner',monthly_requests=2,
                                   max_output_tokens=250)
        self.app=BAMAIRevisionWSGI(workflow=self.workflow,
            plan_resolver=resolve,enabled=True,clock=lambda:1794355200)
    def call(self,*,app=None,body=None,raw=None,**changes):
        if raw is None:
            if body is None:
                body={'draft_id':'a'*32,'expected_revision':1,
                      'target':'post_text','instruction':'Shorter, please',
                      'topic':'Tumblers'}
            raw=json.dumps(body).encode('utf-8')
        env={'wsgi.url_scheme':'https',
             'PATH_INFO':'/api/v1/ai/targeted-revision',
             'REQUEST_METHOD':'POST','CONTENT_TYPE':'application/json',
             'CONTENT_LENGTH':str(len(raw)),'wsgi.input':io.BytesIO(raw),
             'HTTP_AUTHORIZATION':'Bearer '+'t'*43,
             'HTTP_IDEMPOTENCY_KEY':'b'*32}
        env.update(changes)
        response={}
        content=b''.join((app or self.app)(env,lambda status,headers:
            response.update(status=status,headers=dict(headers))))
        return response,json.loads(content)

    def test_strict_success_only_returns_held_metadata(self):
        meta,value=self.call()
        self.assertEqual(meta['status'],'201 Created')
        self.assertEqual(value,{'revised':True,'tenant_id':'shop',
            'draft_id':'a'*32,'revision':2,'status':'needs_media',
            'publishing_enabled':False})
        self.assertEqual(meta['headers']['Cache-Control'],'no-store, private')
        self.assertEqual(self.resolved,[{
            'session_token':'t'*43,'server_now':1794355200}])
        args=self.workflow.calls[0]
        self.assertEqual(args['month'],'2026-11')
        self.assertEqual(args['target'],'post_text')
        self.assertEqual(args['request_key'],'b'*32)
        self.assertEqual(args['sponsorship_plan'].max_output_tokens,250)
        self.assertNotIn('api_key',str(meta)+str(value))
        self.workflow.result='hold'
        meta,value=self.call()
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(value['reason'],'already_in_progress')
        self.assertFalse(value['publishing_enabled'])

    def test_budget_hold_and_operator_pause_survive_strict_transport(self):
        self.workflow.result='hold'
        for reason in ('operator_paused','tenant_estimated_budget_reached',
                       'operator_limit_reached','limit_reached',
                       'historical_estimated_cost_unknown'):
            self.workflow.hold_reason=reason
            meta,value=self.call()
            self.assertEqual(meta['status'],'200 OK')
            self.assertEqual(value['reason'],reason)
            self.assertFalse(value['publishing_enabled'])
        self.workflow.hold_reason='private-vault-token'
        meta,value=self.call()
        self.assertEqual(meta['status'],'503 Service Unavailable')
        self.assertNotIn('vault',str(value))
        self.workflow.result='success'

    def test_transport_and_body_rejections_do_not_resolve_plan(self):
        disabled=BAMAIRevisionWSGI(workflow=self.workflow,
            plan_resolver=lambda **kwargs:self.resolved.append(kwargs),
            enabled=False)
        self.assertEqual(self.call(app=disabled)[0]['status'],
                         '503 Service Unavailable')
        for changes,expected in (
            ({'wsgi.url_scheme':'http',
              'HTTP_X_FORWARDED_PROTO':'https'},'403 Forbidden'),
            ({'PATH_INFO':'/api/v1/ai/publish'},'404 Not Found'),
            ({'REQUEST_METHOD':'PUT'},'405 Method Not Allowed'),
            ({'HTTP_AUTHORIZATION':'Bearer bad'},'401 Unauthorized'),
            ({'HTTP_IDEMPOTENCY_KEY':'wrong'},'400 Bad Request'),
            ({'CONTENT_TYPE':'text/plain'},'400 Bad Request'),
            ({'CONTENT_LENGTH':'999999'},'400 Bad Request')
        ):
            self.assertEqual(self.call(**changes)[0]['status'],expected)
        for extra in ('tenant_id','subject_id','model','api_key',
                      'publish_now','approval','quota','month','role'):
            body={'draft_id':'a'*32,'expected_revision':1,
                  'target':'post_text','instruction':'Shorten','topic':'Product',
                  extra:'untrusted'}
            self.assertEqual(self.call(body=body)[0]['status'],'400 Bad Request')
        for invalid in ({'target':'publish'},
                        {'target':'both'},
                        {'draft_id':'bad'},
                        {'expected_revision':True},
                        {'expected_revision':0},
                        {'instruction':' '},
                        {'instruction':'A'*501}):
            body={'draft_id':'a'*32,'expected_revision':1,
                  'target':'post_text','instruction':'Shorten','topic':'Product',
                  **invalid}
            self.assertEqual(self.call(body=body)[0]['status'],'400 Bad Request')
        for raw in (b'{"target":"post_text","target":"image_prompt"}',
                    b'[]',b'{'):
            self.assertEqual(self.call(raw=raw)[0]['status'],'400 Bad Request')
        self.assertEqual(self.workflow.calls,[])
        self.assertEqual(self.resolved,[])

    def test_failure_mapping_and_no_private_leak(self):
        self.workflow.problem=ValueError('Draft changed; refresh before revising')
        self.assertEqual(self.call()[0]['status'],'409 Conflict')
        self.workflow.problem=PermissionError('Secret tenant info')
        meta,val=self.call()
        self.assertEqual(meta['status'],'401 Unauthorized')
        self.assertNotIn('Secret tenant info',str(val))
        self.workflow.problem=RuntimeError('Vault private key')
        meta,val=self.call()
        self.assertEqual(meta['status'],'503 Service Unavailable')
        self.assertNotIn('Vault',str(val))
        self.workflow.problem=None
        self.workflow.result='malformed'
        self.workflow.revise_sponsored=lambda **kwargs:{
            'revised':True,'tenant_id':'shop',
            'draft':{'draft_id':kwargs['draft_id'],
                     'tenant_id':'shop','revision':2,
                     'status':'published','publishing_enabled':True},
            'publishing_enabled':True}
        self.assertEqual(self.call()[0]['status'],'503 Service Unavailable')
        with self.assertRaises(ValueError):
            BAMAIRevisionWSGI(workflow=self.workflow,
                plan_resolver=lambda **kwargs:None,enabled=1)

if __name__=='__main__':
    unittest.main()
