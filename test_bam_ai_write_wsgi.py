import io
import json
import unittest
from bam_ai_write_wsgi import BAMAIWriteWSGI
from ai_sponsorship import SponsorshipPlan

class FakeWorkflow:
    def __init__(self):
        self.calls=[]
        self.hold_reason=None
    def generate_sponsored(self,**kwargs):
        self.calls.append(kwargs)
        if kwargs['token']!='valid':
            raise PermissionError('invalid')
        if self.hold_reason is not None:
            return {'created':False,'tenant_id':'shop',
                    'reason':self.hold_reason,'publishing_enabled':False}
        return {'created':True,'draft':{
            'tenant_id':'shop','draft_id':'a'*32,'status':'needs_media',
            'publishing_enabled':False}}

class BAMAIWriteWSGITests(unittest.TestCase):
    def setUp(self):
        self.workflow=FakeWorkflow()
        self.plans=[]
        def resolve(**kwargs):
            self.plans.append(kwargs)
            return SponsorshipPlan('owner',2,500)
        self.app=BAMAIWriteWSGI(workflow=self.workflow,
            plan_resolver=resolve,enabled=True,clock=lambda:1794355200)

    def call(self,*,app=None,body=None,**changes):
        if body is None:
            body={'topic':'Tumblers','platform':'facebook',
                'needs_media':True,'include_image_prompt':True}
        raw=json.dumps(body).encode()
        env={'wsgi.url_scheme':'https','PATH_INFO':'/api/v1/ai-generate',
             'REQUEST_METHOD':'POST','HTTP_AUTHORIZATION':'Bearer valid',
             'HTTP_IDEMPOTENCY_KEY':'b'*32,
             'CONTENT_TYPE':'application/json',
             'CONTENT_LENGTH':str(len(raw)),'wsgi.input':io.BytesIO(raw)}
        env.update(changes)
        captured=[]
        def start(status,headers):
            captured.append((status,dict(headers)))
        data=b''.join((app or self.app)(env,start))
        return captured[0],json.loads(data)

    def test_success_is_unpublished_and_uses_server_month(self):
        (status,headers),body=self.call()
        self.assertEqual(status,'201 Created')
        self.assertEqual(body['draft_id'],'a'*32)
        self.assertFalse(body['publishing_enabled'])
        self.assertEqual(headers['Cache-Control'],'no-store, private')
        call=self.workflow.calls[0]
        self.assertEqual(call['request_key'],'b'*32)
        self.assertEqual(call['month'],'2026-11')
        self.assertEqual(call['sponsorship_plan'].monthly_requests,2)
        self.assertNotIn('api_key',str(body))

    def test_sponsorship_hold_is_safe_and_reasons_are_allowlisted(self):
        for reason in ('operator_paused','tenant_limit_reached',
                       'operator_estimated_budget_reached',
                       'historical_estimated_cost_unknown',
                       'already_completed'):
            self.workflow.hold_reason=reason
            (status,_),value=self.call()
            self.assertEqual(status,'200 OK')
            self.assertEqual(value,{'created':False,'tenant_id':'shop',
                'reason':reason,'publishing_enabled':False})
        self.workflow.hold_reason='vault:private-credential'
        (status,_),value=self.call()
        self.assertEqual(status,'503 Service Unavailable')
        self.assertNotIn('credential',str(value))
        self.workflow.hold_reason=None

    def test_disabled_endpoint_never_resolves_plan(self):
        app=BAMAIWriteWSGI(workflow=self.workflow,
            plan_resolver=lambda **kw:self.plans.append(kw),
            enabled=False)
        (status,_),body=self.call(app=app)
        self.assertEqual(status,'503 Service Unavailable')
        self.assertEqual(self.plans,[])
        self.assertEqual(self.workflow.calls,[])

    def test_rejects_client_scope_and_publishing_claims(self):
        for extra in ({'tenant_id':'other'},
                      {'publishing_enabled':True},
                      {'model':'unapproved'}):
            with self.subTest(extra=extra):
                body={'topic':'Tumblers','platform':'facebook',
                    'needs_media':True,'include_image_prompt':True,**extra}
                (status,_),_=self.call(body=body)
                self.assertEqual(status,'400 Bad Request')
        self.assertEqual(self.workflow.calls,[])

    def test_auth_and_request_key_required(self):
        for change,expected in [
            ({'HTTP_AUTHORIZATION':'Bearer invalid'},'401 Unauthorized'),
            ({'HTTP_IDEMPOTENCY_KEY':''},'400 Bad Request'),
            ({'wsgi.url_scheme':'http'},'403 Forbidden'),
            ({'REQUEST_METHOD':'GET'},'405 Method Not Allowed'),
            ({'CONTENT_LENGTH':'9'*10000},'413 Content Too Large')]:
            (status,_),_=self.call(**change)
            self.assertEqual(status,expected)

    def test_duplicate_json_fields_rejected(self):
        raw=b'{"topic":"Tumblers","topic":"Hidden","platform":"facebook","needs_media":true,"include_image_prompt":true}'
        (status,_),_=self.call(**{
            'CONTENT_LENGTH':str(len(raw)),
            'wsgi.input':io.BytesIO(raw)})
        self.assertEqual(status,'400 Bad Request')

if __name__=='__main__':
    unittest.main()
