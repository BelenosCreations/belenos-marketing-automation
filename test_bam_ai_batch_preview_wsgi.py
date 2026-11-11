"""Safe, zero-cost batch-preview transport tests."""
import io
import json
import unittest
from bam_ai_batch_preview_wsgi import BAMAIBatchPreviewWSGI

class FakeAPI:
    def __init__(self):
        self.calls=[]
        self.problem=None
        self.unsafe=False
    def preview_ai_batch(self,**kwargs):
        self.calls.append(kwargs)
        if self.problem:
            raise self.problem
        return {'tenant_id':'shop','mode':'bam_sponsored',
                'fact_revision':3,'fact_provenance':'owner_confirmed',
                'items':[{'topic':topic,'platform':kwargs['platform'],
                          'image_prompt_planned':kwargs['include_image_prompt']}
                         for topic in kwargs['topics']],
                'planned_individual_requests':len(kwargs['topics']),
                'provider_requests_made':1 if self.unsafe else 0,
                'quota_reserved':False,'actual_cost_known':False,
                'drafts_created':0,'status':'planning_only',
                'publishing_enabled':False}

class BatchPreviewWSGITests(unittest.TestCase):
    def setUp(self):
        self.api=FakeAPI()
        self.app=BAMAIBatchPreviewWSGI(
            self.api,enabled=True,clock=lambda:101)
    def call(self,*,app=None,body=None,raw=None,**changes):
        if raw is None:
            if body is None:
                body={'topics':['Gift ideas','Custom tumblers'],
                      'platform':'facebook','include_image_prompt':True}
            raw=json.dumps(body).encode()
        env={'wsgi.url_scheme':'https',
             'PATH_INFO':'/api/v1/ai/batch-preview',
             'REQUEST_METHOD':'POST','CONTENT_TYPE':'application/json',
             'CONTENT_LENGTH':str(len(raw)),'wsgi.input':io.BytesIO(raw),
             'HTTP_AUTHORIZATION':'Bearer '+'t'*43}
        env.update(changes)
        metadata={}
        output=b''.join((app or self.app)(env,lambda status,headers:
            metadata.update(status=status,headers=dict(headers))))
        return metadata,json.loads(output)

    def test_trusted_read_only_preview(self):
        response,body=self.call()
        self.assertEqual(response['status'],'200 OK')
        self.assertEqual(response['headers']['Cache-Control'],'no-store, private')
        self.assertEqual(body['planned_individual_requests'],2)
        self.assertEqual(body['provider_requests_made'],0)
        self.assertEqual(body['drafts_created'],0)
        self.assertFalse(body['publishing_enabled'])
        self.assertIs(body['quota_reserved'],False)
        self.assertIs(body['actual_cost_known'],False)
        self.assertEqual(self.api.calls[0],{
            'session_token':'t'*43,'server_now':101,
            'topics':['Gift ideas','Custom tumblers'],
            'platform':'facebook','include_image_prompt':True})

    def test_disabled_authentication_and_forged_fields_fail(self):
        self.assertEqual(self.call(app=BAMAIBatchPreviewWSGI(self.api))[0]
                         ['status'],'503 Service Unavailable')
        for changes,expected in [
                ({'wsgi.url_scheme':'http',
                  'HTTP_X_FORWARDED_PROTO':'https'},'403 Forbidden'),
                ({'PATH_INFO':'/api/v1/publish'},'404 Not Found'),
                ({'REQUEST_METHOD':'GET'},'405 Method Not Allowed'),
                ({'HTTP_AUTHORIZATION':'Bearer bad'},'401 Unauthorized'),
                ({'CONTENT_TYPE':'text/plain'},'400 Bad Request'),
                ({'CONTENT_LENGTH':'100000'},'400 Bad Request'),
                ({'QUERY_STRING':'tenant_id=other'},'400 Bad Request')]:
            self.assertEqual(self.call(**changes)[0]['status'],expected)
        for field in ('tenant_id','model','approved','publish_now',
                      'api_key','monthly_limit','cost_estimate'):
            self.assertEqual(self.call(body={
                'topics':['Gift ideas'],'platform':'facebook',
                'include_image_prompt':True,field:'forged'})[0]['status'],
                '400 Bad Request')
        for invalid in (
                {'topics':[]},
                {'topics':['Same','same']},
                {'topics':['bad ']},
                {'topics':['a']*15},
                {'platform':'unsupported'},
                {'include_image_prompt':'yes'},
                {'topics':[True]}):
            request={'topics':['Gift ideas'],
                    'platform':'facebook','include_image_prompt':True}
            self.assertEqual(self.call(body={**request,**invalid})[0]
                             ['status'],'400 Bad Request')
        for malformed in (
                b'{"topics":[],"topics":["Oops"]}',
                b'{"topics":["x"],"platform":"facebook","platform":"tiktok","include_image_prompt":true}',
                b'[]',b'{'):
            self.assertEqual(self.call(raw=malformed)[0]['status'],
                             '400 Bad Request')
        self.assertEqual(self.api.calls,[])

    def test_unsafe_result_and_permission_denial(self):
        self.api.unsafe=True
        self.assertEqual(self.call()[0]['status'],'503 Service Unavailable')
        self.api.unsafe=False
        self.api.problem=PermissionError('Private business')
        meta,value=self.call()
        self.assertEqual(meta['status'],'401 Unauthorized')
        self.assertNotIn('Private business',str(value))
        with self.assertRaises(ValueError):
            BAMAIBatchPreviewWSGI(self.api,enabled=1)

if __name__=='__main__':
    unittest.main()
