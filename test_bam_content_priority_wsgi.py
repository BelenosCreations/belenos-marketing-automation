"""Offline strict HTTP queue priority boundary tests."""
import io
import json
import unittest
from bam_content_priority_wsgi import BAMContentPriorityWSGI

RID='a'*32
OLD='b'*32
NEW='c'*32

class FakeAPI:
    def __init__(self):
        self.calls=[]
        self.denied=False
        self.conflict=False
        self.unsafe=False
    def update_held_priority(self,**kwargs):
        self.calls.append(kwargs)
        if self.denied:
            raise PermissionError('Not in business')
        if self.conflict:
            raise ValueError('Queue priority changed; refresh required')
        return {'tenant_id':'shop','request_id':kwargs['request_id'],
            'priority':kwargs['priority'],
            'priority_token':NEW if not self.unsafe else OLD,
            'revision':3,'status':'held_priority_only',
            'publishing_enabled':False}

class PriorityTransportTests(unittest.TestCase):
    def setUp(self):
        self.api=FakeAPI()
        self.app=BAMContentPriorityWSGI(
            self.api,enabled=True,clock=lambda:101)
    def call(self,app=None,body=None,raw=None,**changes):
        if raw is None:
            if body is None:
                body={'request_id':RID,'priority':2,
                      'expected_priority_token':OLD}
            raw=json.dumps(body).encode('utf-8')
        env={'wsgi.url_scheme':'https',
             'PATH_INFO':'/api/v1/content/priority',
             'REQUEST_METHOD':'PUT','HTTP_AUTHORIZATION':'Bearer '+'t'*43,
             'CONTENT_TYPE':'application/json',
             'CONTENT_LENGTH':str(len(raw)),'wsgi.input':io.BytesIO(raw)}
        env.update(changes)
        meta={}
        response=b''.join((app or self.app)(env,lambda status,headers:
            meta.update(status=status,headers=dict(headers))))
        return meta,json.loads(response)
    def test_write_never_approves_or_publishes(self):
        meta,result=self.call()
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(meta['headers']['Cache-Control'],'no-store, private')
        self.assertEqual(result['status'],'held_priority_only')
        self.assertEqual(result['priority'],2)
        self.assertEqual(result['revision'],3)
        self.assertFalse(result['publishing_enabled'])
        self.assertEqual(self.api.calls,[{
            'session_token':'t'*43,'server_now':101,
            'request_id':RID,'priority':2,
            'expected_priority_token':OLD}])
    def test_http_restrictions_and_conflicts(self):
        self.assertEqual(self.call(app=BAMContentPriorityWSGI(
            self.api))[0]['status'],'503 Service Unavailable')
        for changes,expected in (
          ({'wsgi.url_scheme':'http',
            'HTTP_X_FORWARDED_PROTO':'https'},'403 Forbidden'),
          ({'REQUEST_METHOD':'GET'},'405 Method Not Allowed'),
          ({'REQUEST_METHOD':'POST'},'405 Method Not Allowed'),
          ({'PATH_INFO':'/api/v1/social/publish'},'404 Not Found'),
          ({'HTTP_AUTHORIZATION':'Bearer bad'},'401 Unauthorized'),
          ({'QUERY_STRING':'tenant_id=other'},'400 Bad Request'),
          ({'CONTENT_TYPE':'text/plain'},'400 Bad Request')
        ):
            self.assertEqual(self.call(**changes)[0]['status'],expected)
        for changes in (
          {'role':'owner'},{'approved':True},{'tenant_id':'other'},
          {'schedule_now':True},{'api_key':'secret'}
        ):
            self.assertEqual(self.call(body={
                'request_id':RID,'priority':2,
                'expected_priority_token':OLD,**changes
            })[0]['status'],'400 Bad Request')
        for item in (True,0.5,11,-11,'2',None):
            self.assertEqual(self.call(body={
                'request_id':RID,'priority':item,
                'expected_priority_token':OLD
            })[0]['status'],'400 Bad Request')
        for token in ('bad',None,True,7):
            self.assertEqual(self.call(body={
                'request_id':RID,'priority':2,
                'expected_priority_token':token
            })[0]['status'],'400 Bad Request')
        self.assertEqual(self.call(raw=b'{"priority":1,"priority":3}')[0]
                         ['status'],'400 Bad Request')
        self.assertEqual(self.api.calls,[])
        self.api.conflict=True
        self.assertEqual(self.call()[0]['status'],'409 Conflict')
        self.api.conflict=False
        self.api.denied=True
        self.assertEqual(self.call()[0]['status'],'401 Unauthorized')
        self.api.denied=False
        self.api.unsafe=True
        self.assertEqual(self.call()[0]['status'],'503 Service Unavailable')

if __name__=='__main__':
    unittest.main()
