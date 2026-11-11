"""Strict no-provider AI writing preferences update transport tests."""
import io
import json
import unittest
from bam_ai_memory_wsgi import BAMAIMemoryWSGI

class FakeAPI:
    def __init__(self):
        self.calls=[]
        self.problem=None
    def edit_ai_memory(self,**kwargs):
        self.calls.append(kwargs)
        if self.problem:
            raise self.problem
        return {'tenant_id':'shop','memory':kwargs['memory'],
                'publishing_enabled':False}

class MemoryTransportTests(unittest.TestCase):
    def setUp(self):
        self.api=FakeAPI()
        self.app=BAMAIMemoryWSGI(self.api,enabled=True,clock=lambda:101)
    def call(self,*,app=None,body=None,raw=None,**changes):
        if raw is None:
            if body is None:
                body={'memory':{'tone':'Short Facebook posts'},
                      'expected_memory':{}}
            raw=json.dumps(body).encode()
        env={'wsgi.url_scheme':'https',
             'PATH_INFO':'/api/v1/ai-memory',
             'REQUEST_METHOD':'PUT','CONTENT_TYPE':'application/json',
             'CONTENT_LENGTH':str(len(raw)),
             'wsgi.input':io.BytesIO(raw),
             'HTTP_AUTHORIZATION':'Bearer '+'t'*43}
        env.update(changes)
        result={}
        payload=b''.join((app or self.app)(env,lambda status,headers:
            result.update(status=status,headers=dict(headers))))
        return result,json.loads(payload)

    def test_authenticated_private_response(self):
        meta,payload=self.call()
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(payload['tenant_id'],'shop')
        self.assertEqual(payload['memory'],{'tone':'Short Facebook posts'})
        self.assertFalse(payload['publishing_enabled'])
        self.assertEqual(meta['headers']['Cache-Control'],'no-store, private')
        self.assertEqual(self.api.calls,[{
            'session_token':'t'*43,'server_now':101,
            'memory':{'tone':'Short Facebook posts'},
            'expected_memory':{}}])

    def test_stale_and_denied_are_sanitized(self):
        self.api.problem=ValueError('AI memory changed; refresh before saving')
        meta,body=self.call()
        self.assertEqual(meta['status'],'409 Conflict')
        self.assertNotIn('Short Facebook posts',str(body))
        self.api.problem=PermissionError('Private owner account')
        meta,body=self.call()
        self.assertEqual(meta['status'],'401 Unauthorized')
        self.assertNotIn('Private owner account',str(body))
        self.api.problem=RuntimeError('Database storage path')
        self.assertEqual(self.call()[0]['status'],'503 Service Unavailable')
        with self.assertRaises(ValueError):
            BAMAIMemoryWSGI(self.api,enabled=1)

    def test_disabled_insecure_and_forged_fields(self):
        self.assertEqual(self.call(app=BAMAIMemoryWSGI(self.api))[0]['status'],
                         '503 Service Unavailable')
        for changes,expected in [
            ({'wsgi.url_scheme':'http',
              'HTTP_X_FORWARDED_PROTO':'https'},'403 Forbidden'),
            ({'PATH_INFO':'/api/v1/publish'},'404 Not Found'),
            ({'REQUEST_METHOD':'POST'},'405 Method Not Allowed'),
            ({'HTTP_AUTHORIZATION':'Bearer bad'},'401 Unauthorized'),
            ({'CONTENT_TYPE':'text/plain'},'400 Bad Request'),
            ({'CONTENT_LENGTH':'99999'},'400 Bad Request')]:
            self.assertEqual(self.call(**changes)[0]['status'],expected)
        for extra in ('tenant_id','subject_id','role','api_key',
                      'publish_now','mode','billing_plan'):
            self.assertEqual(self.call(body={
                'memory':{'tone':'Short Facebook posts'},
                'expected_memory':{},extra:'forged'})[0]['status'],
                '400 Bad Request')
        for raw in (
            b'{"memory":{},"memory":{},"expected_memory":{}}',
            b'{"memory":{"tone":"Short","tone":"Long"},"expected_memory":{}}',
            b'[]',b'{'):
            self.assertEqual(self.call(raw=raw)[0]['status'],
                             '400 Bad Request')
        self.assertEqual(self.api.calls,[])

if __name__=='__main__':
    unittest.main()
