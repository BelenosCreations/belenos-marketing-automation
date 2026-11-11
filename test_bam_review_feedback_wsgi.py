"""Private feedback HTTP boundary rejects spoofed approvals and stale writes."""
import io
import json
import unittest
from bam_review_feedback_wsgi import BAMReviewFeedbackWSGI

RID='a'*32
VERSION='b'*32

class Fake:
    def __init__(self):
        self.calls=[]
        self.denied=False
        self.conflict=False
        self.unsafe=False
    def list_current_business(self,**kwargs):
        self.calls.append(('read',kwargs))
        if self.denied:
            raise PermissionError('denied')
        return {'tenant_id':'shop','status':'feedback_only',
           'items':[{'request_id':RID,'draft_revision':1,
             'current_revision':2,'stale':True,
             'note':'Verify the description','feedback_token':VERSION,
             'updated_at':100,'approval_granted':False,
             'publishing_enabled':self.unsafe}],
           'approval_granted':False,'publishing_enabled':False}
    def history_current_business(self,**kwargs):
        self.calls.append(('history',kwargs))
        if self.denied:
            raise PermissionError('owner required')
        return {'tenant_id':'shop','status':'feedback_history_only',
                'events':[{'event_id':'c'*32,'request_id':RID,
                           'action':'updated','draft_revision':2,
                           'occurred_at':102}],
                'truncated':False,
                'approval_granted':self.unsafe,
                'publishing_enabled':False}
    def save(self,**kwargs):
        self.calls.append(('save',kwargs))
        if self.denied:
            raise PermissionError('denied')
        if self.conflict:
            raise ValueError('Feedback changed; refresh required')
        return {'tenant_id':'shop','request_id':kwargs['request_id'],
           'draft_revision':kwargs['expected_revision'],
           'feedback_token':VERSION,'status':'feedback_only',
           'approval_granted':self.unsafe,'publishing_enabled':False}
    def discard(self,**kwargs):
        self.calls.append(('discard',kwargs))
        if self.denied:
            raise PermissionError('denied')
        if self.conflict:
            raise ValueError('Feedback changed; refresh required')
        return {'tenant_id':'shop','request_id':kwargs['request_id'],
           'removed':1,'status':'feedback_only',
           'approval_granted':False,'publishing_enabled':self.unsafe}

class FeedbackTransportTests(unittest.TestCase):
    def setUp(self):
        self.service=Fake()
        self.app=BAMReviewFeedbackWSGI(
            self.service,enabled=True,clock=lambda:103)
    def call(self,method='GET',body=None,raw=None,app=None,**extra):
        if body is None:
            body=({'request_id':RID,'expected_revision':2,
                'expected_feedback_token':VERSION,'note':'Review the artwork'}
                if method=='PUT'
                else {'request_id':RID,'expected_feedback_token':VERSION})
        if raw is None:
            raw=json.dumps(body).encode()
        env={'PATH_INFO':'/api/v1/review-feedback',
           'REQUEST_METHOD':method,'wsgi.url_scheme':'https',
           'HTTP_AUTHORIZATION':'Bearer '+'t'*43,
           'CONTENT_TYPE':'application/json',
           'CONTENT_LENGTH':str(len(raw)),
           'wsgi.input':io.BytesIO(raw)}
        env.update(extra)
        output={}
        data=b''.join((app or self.app)(env,lambda status,headers:
            output.update(status=status,headers=dict(headers))))
        return output,json.loads(data)

    def test_read_and_explicit_write_are_never_approval(self):
        meta,read=self.call()
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(meta['headers']['Cache-Control'],'no-store, private')
        self.assertTrue(read['items'][0]['stale'])
        self.assertFalse(read['approval_granted'])
        meta,save=self.call('PUT')
        self.assertEqual(meta['status'],'200 OK')
        self.assertFalse(save['approval_granted'])
        self.assertEqual(self.service.calls[-1],('save',{
            'token':'t'*43,'now':103,'request_id':RID,
            'expected_revision':2,'expected_feedback_token':VERSION,
            'note':'Review the artwork'}))
        meta,deleted=self.call('DELETE')
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(deleted['removed'],1)
        self.assertFalse(deleted['publishing_enabled'])

    def test_history_is_owner_only_nonapproval_metadata(self):
        path='/api/v1/review-feedback-history'
        meta,data=self.call(PATH_INFO=path)
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(meta['headers']['Cache-Control'],'no-store, private')
        self.assertEqual(data['events'][0]['action'],'updated')
        self.assertEqual(data['events'][0]['draft_revision'],2)
        self.assertFalse(data['approval_granted'])
        self.assertFalse(data['publishing_enabled'])
        self.assertNotIn('note',str(data))
        self.assertEqual(self.service.calls[-1],(
            'history',{'token':'t'*43,'now':103}))
        self.assertEqual(self.call(PATH_INFO=path,
            REQUEST_METHOD='PUT')[0]['status'],'405 Method Not Allowed')
        self.assertEqual(self.call(PATH_INFO=path,
            QUERY_STRING='tenant_id=other')[0]['status'],'400 Bad Request')
        self.service.unsafe=True
        self.assertEqual(self.call(PATH_INFO=path)[0]['status'],
                         '503 Service Unavailable')
        self.service.unsafe=False
        self.service.denied=True
        self.assertEqual(self.call(PATH_INFO=path)[0]['status'],
                         '401 Unauthorized')

    def test_forged_write_and_invalid_transport_fail_closed(self):
        for extra,status in [
            ({'wsgi.url_scheme':'http','HTTP_X_FORWARDED_PROTO':'https'},
             '403 Forbidden'),
            ({'PATH_INFO':'/api/v1/publish'},'404 Not Found'),
            ({'REQUEST_METHOD':'POST'},'405 Method Not Allowed'),
            ({'QUERY_STRING':'tenant_id=other'},'400 Bad Request'),
            ({'HTTP_AUTHORIZATION':'Bearer bad'},'401 Unauthorized')]:
            self.assertEqual(self.call(**extra)[0]['status'],status)
        for forbidden in ('tenant_id','actor_role','approved','publish',
                          'schedule_at','publishing_enabled','api_key'):
            self.assertEqual(self.call('PUT',body={
                'request_id':RID,'expected_revision':2,
                'expected_feedback_token':VERSION,'note':'Review',
                forbidden:True})[0]['status'],'400 Bad Request')
        for wrong in (None,123,True,'bad'):
            self.assertEqual(self.call('DELETE',body={
                'request_id':RID,'expected_feedback_token':wrong
            })[0]['status'],'400 Bad Request')
        for bad_note in ('',' padded ','bad\u0000note','x'*1001):
            self.assertEqual(self.call('PUT',body={
                'request_id':RID,'expected_revision':2,
                'expected_feedback_token':None,'note':bad_note
            })[0]['status'],'400 Bad Request')
        self.assertEqual(self.call('PUT',raw=b'{"note":"a","note":"b"}')[0]
                         ['status'],'400 Bad Request')
        self.assertEqual(self.call(app=BAMReviewFeedbackWSGI())[0]
                         ['status'],'503 Service Unavailable')
        self.assertEqual(self.service.calls,[])

    def test_stale_write_denied_and_unsafe_service_rejected(self):
        self.service.conflict=True
        self.assertEqual(self.call('PUT')[0]['status'],'409 Conflict')
        self.assertEqual(self.call('DELETE')[0]['status'],'409 Conflict')
        self.service.conflict=False
        self.service.unsafe=True
        for method in ('GET','PUT','DELETE'):
            self.assertEqual(self.call(method)[0]['status'],
                             '503 Service Unavailable')
        self.service.unsafe=False
        self.service.denied=True
        self.assertEqual(self.call()[0]['status'],'401 Unauthorized')
        with self.assertRaises(ValueError):
            BAMReviewFeedbackWSGI(self.service,enabled=1)

if __name__=='__main__':
    unittest.main()
