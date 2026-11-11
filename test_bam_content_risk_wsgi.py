"""Strict read-only claim-risk transport, never posting permission."""
import json
import unittest
from bam_content_risk_wsgi import BAMContentRiskWSGI

class FakeAPI:
    def __init__(self):
        self.calls=[]
        self.denied=False
        self.unsafe=False
    def get_content_risk_preview(self,**kwargs):
        self.calls.append(kwargs)
        if self.denied:
            raise PermissionError('Denied tenant')
        return {'tenant_id':'shop','request_id':kwargs['request_id'],
            'revision':2,
            'signals':[{'category':'price_or_discount',
                        'start':0,'end':3,'text':'$18'}],
            'signal_count':1,'truncated':False,
            'review_required':True,'extraction_complete':False,
            'status':'held','publishing_enabled':self.unsafe}

class RiskWSGITests(unittest.TestCase):
    def setUp(self):
        self.api=FakeAPI()
        self.app=BAMContentRiskWSGI(
            self.api,enabled=True,clock=lambda:101)
    def call(self,*,app=None,**changes):
        environ={'wsgi.url_scheme':'https',
            'PATH_INFO':'/api/v1/content/risk-preview',
            'REQUEST_METHOD':'GET','QUERY_STRING':'request_id='+'a'*32,
            'HTTP_AUTHORIZATION':'Bearer '+'t'*43}
        environ.update(changes)
        got={}
        raw=b''.join((app or self.app)(environ,lambda status,headers:
            got.update(status=status,headers=dict(headers))))
        return got,json.loads(raw)
    def test_private_heuristic_preview(self):
        meta,payload=self.call()
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(payload['signals'][0]['text'],'$18')
        self.assertEqual(payload['status'],'held')
        self.assertTrue(payload['review_required'])
        self.assertFalse(payload['extraction_complete'])
        self.assertFalse(payload['publishing_enabled'])
        self.assertEqual(self.api.calls[0]['request_id'],'a'*32)
        self.assertEqual(meta['headers']['Cache-Control'],'no-store, private')
    def test_transport_permissions_and_no_client_claims(self):
        self.assertEqual(self.call(app=BAMContentRiskWSGI(self.api))[0]
                         ['status'],'503 Service Unavailable')
        for changes,status in [
            ({'REQUEST_METHOD':'POST'},'405 Method Not Allowed'),
            ({'wsgi.url_scheme':'http',
              'HTTP_X_FORWARDED_PROTO':'https'},'403 Forbidden'),
            ({'HTTP_AUTHORIZATION':'Bearer invalid'},'401 Unauthorized'),
            ({'QUERY_STRING':'tenant_id=other&request_id='+'a'*32},
             '400 Bad Request'),
            ({'QUERY_STRING':'request_id='+'a'*32+'&request_id='+'b'*32},
             '400 Bad Request'),
            ({'QUERY_STRING':'request_id=bad'},'400 Bad Request'),
            ({'QUERY_STRING':'request_id='+'a'*32+'&publish_now=true'},
             '400 Bad Request')]:
            self.assertEqual(self.call(**changes)[0]['status'],status)
    def test_unsafe_response_denied(self):
        self.api.unsafe=True
        self.assertEqual(self.call()[0]['status'],'503 Service Unavailable')
        self.api.denied=True
        self.assertEqual(self.call()[0]['status'],'401 Unauthorized')
        with self.assertRaises(ValueError):
            BAMContentRiskWSGI(self.api,enabled=1)

if __name__=='__main__':
    unittest.main()
