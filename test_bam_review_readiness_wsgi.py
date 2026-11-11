"""Review readiness endpoint is a strict private read-only safety preview."""
import json
import unittest
from bam_review_readiness_wsgi import BAMReviewReadinessWSGI

RID='a'*32
class Fake:
    def __init__(self):
        self.calls=[]
        self.denied=False
        self.unsafe=False
    def list_current_business(self,**kwargs):
        self.calls.append(kwargs)
        if self.denied:
            raise PermissionError('other tenant')
        return {'tenant_id':'shop','status':'review_preview_only',
             'held_count':1,'editorial_material_complete_count':0,
             'items':[{'request_id':RID,'revision':1,'channel':'facebook',
               'status':'needs_content','missing_items':['image'],
               'unverified_items':[],
               'editorial_material_complete':False,
               'blockers':['missing_required_content',
                 'truthguard_review_required','owner_approval_not_implemented',
                 'social_publishing_disabled'],
               'approved':self.unsafe,'publishing_enabled':False}],
             'approved_count':0,'publishing_enabled':False}
class ReviewReadinessTransportTests(unittest.TestCase):
    def setUp(self):
        self.svc=Fake()
        self.app=BAMReviewReadinessWSGI(
            self.svc,enabled=True,clock=lambda:103)
    def call(self,app=None,**changes):
        env={'PATH_INFO':'/api/v1/review-readiness',
            'REQUEST_METHOD':'GET','wsgi.url_scheme':'https',
            'HTTP_AUTHORIZATION':'Bearer '+'t'*43}
        env.update(changes)
        details={}
        raw=b''.join((app or self.app)(env,lambda status,headers:
            details.update(status=status,headers=dict(headers))))
        return details,json.loads(raw)
    def test_private_preview_cannot_approve(self):
        meta,result=self.call()
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(meta['headers']['Cache-Control'],'no-store, private')
        self.assertEqual(self.svc.calls,[
            {'token':'t'*43,'now':103}])
        self.assertEqual(result['approved_count'],0)
        self.assertFalse(result['publishing_enabled'])
        self.assertIn('truthguard_review_required',
            result['items'][0]['blockers'])
    def test_invalid_requests_and_forged_results(self):
        for change,status in [
            ({'wsgi.url_scheme':'http','HTTP_X_FORWARDED_PROTO':'https'},
             '403 Forbidden'),
            ({'REQUEST_METHOD':'POST'},'405 Method Not Allowed'),
            ({'PATH_INFO':'/api/v1/approve'},'404 Not Found'),
            ({'QUERY_STRING':'tenant_id=other'},'400 Bad Request'),
            ({'HTTP_AUTHORIZATION':'Bearer invalid'},'401 Unauthorized')]:
            self.assertEqual(self.call(**change)[0]['status'],status)
        self.assertEqual(self.call(app=BAMReviewReadinessWSGI())[0]
                         ['status'],'503 Service Unavailable')
        self.svc.unsafe=True
        self.assertEqual(self.call()[0]['status'],'503 Service Unavailable')
        self.svc.unsafe=False
        self.svc.denied=True
        self.assertEqual(self.call()[0]['status'],'401 Unauthorized')
        with self.assertRaises(ValueError):
            BAMReviewReadinessWSGI(self.svc,enabled=1)

if __name__=='__main__':
    unittest.main()
