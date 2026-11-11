"""Non-executable, strict calendar proposal HTTP boundary tests."""
import io
import json
import unittest
from bam_calendar_proposals_wsgi import BAMCalendarProposalsWSGI

RID='a'*32
UTC='2026-11-11T15:00:00+00:00'

class FakeService:
    def __init__(self):
        self.calls=[]
        self.denied=False
        self.unsafe=False
    def list_mine_business(self,**kwargs):
        self.calls.append(('read',kwargs))
        if self.denied:
            raise PermissionError('private account')
        return {'tenant_id':'shop','status':'proposal_only',
                'items':[{'request_id':RID,'draft_revision':1,
                    'current_revision':1,'utc_at':UTC,
                    'local_date':'2026-11-11','local_time':'10:00',
                    'timezone':'America/New_York',
                    'content_changed':False,'slot_current':True,
                    'publishing_enabled':False}],
                'posts_scheduled':1 if self.unsafe else 0,
                'publishing_enabled':False}
    def propose(self,**kwargs):
        self.calls.append(('propose',kwargs))
        if self.denied:
            raise PermissionError('private account')
        return {'tenant_id':'shop','request_id':kwargs['request_id'],
                'utc_at':kwargs['utc_at'],'status':'proposal_only',
                'posts_scheduled':1 if self.unsafe else 0,
                'publishing_enabled':False}
    def discard(self,**kwargs):
        self.calls.append(('discard',kwargs))
        if self.denied:
            raise PermissionError('private account')
        return {'tenant_id':'shop','request_id':kwargs['request_id'],
                'removed':1,'status':'proposal_only',
                'posts_scheduled':1 if self.unsafe else 0,
                'publishing_enabled':False}

class CalendarProposalTransportTests(unittest.TestCase):
    def setUp(self):
        self.service=FakeService()
        self.app=BAMCalendarProposalsWSGI(
            self.service,enabled=True,clock=lambda:101)
    def call(self,*,app=None,method='GET',body=None,raw=None,**changes):
        if raw is None:
            if body is None:
                body=({'request_id':RID,'expected_revision':1,'utc_at':UTC}
                      if method=='POST' else {'request_id':RID})
            raw=json.dumps(body).encode()
        env={'wsgi.url_scheme':'https','PATH_INFO':'/api/v1/calendar-proposals',
             'REQUEST_METHOD':method,'CONTENT_TYPE':'application/json',
             'CONTENT_LENGTH':str(len(raw)),'wsgi.input':io.BytesIO(raw),
             'HTTP_AUTHORIZATION':'Bearer '+'t'*43}
        env.update(changes)
        captured={}
        result=b''.join((app or self.app)(env,lambda status,headers:
            captured.update(status=status,headers=dict(headers))))
        return captured,json.loads(result)
    def test_read_create_delete_are_private_and_nonpublishing(self):
        meta,listed=self.call()
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(meta['headers']['Cache-Control'],'no-store, private')
        self.assertEqual(listed['items'][0]['slot_current'],True)
        self.assertEqual(listed['posts_scheduled'],0)
        meta,created=self.call(method='POST')
        self.assertEqual(meta['status'],'201 Created')
        self.assertEqual(created['status'],'proposal_only')
        self.assertEqual(created['posts_scheduled'],0)
        self.assertEqual(self.service.calls[-1][1],{
            'token':'t'*43,'now':101,'request_id':RID,
            'expected_revision':1,'utc_at':UTC})
        meta,deleted=self.call(method='DELETE')
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(deleted['removed'],1)
        self.assertFalse(deleted['publishing_enabled'])
        self.assertEqual(self.service.calls[-1][1],{
            'token':'t'*43,'now':101,'request_id':RID})

    def test_invalid_transport_and_spoofed_approval_rejected(self):
        self.assertEqual(self.call(app=BAMCalendarProposalsWSGI())[0]
                         ['status'],'503 Service Unavailable')
        for changes,status in [
            ({'wsgi.url_scheme':'http','HTTP_X_FORWARDED_PROTO':'https'},
             '403 Forbidden'),
            ({'PATH_INFO':'/api/v1/publish'},'404 Not Found'),
            ({'REQUEST_METHOD':'PATCH'},'405 Method Not Allowed'),
            ({'HTTP_AUTHORIZATION':'Bearer bad'},'401 Unauthorized'),
            ({'QUERY_STRING':'tenant_id=other'},'400 Bad Request'),
        ]:
            self.assertEqual(self.call(**changes)[0]['status'],status)
        for extra in ('tenant_id','role','approved','publish_now',
                      'schedule_job_id','api_key'):
            self.assertEqual(self.call(method='POST',body={
                'request_id':RID,'expected_revision':1,
                'utc_at':UTC,extra:'forged'})[0]['status'],
                '400 Bad Request')
        for bad in (
            {'request_id':'bad','expected_revision':1,'utc_at':UTC},
            {'request_id':RID,'expected_revision':True,'utc_at':UTC},
            {'request_id':RID,'expected_revision':0,'utc_at':UTC},
            {'request_id':RID,'expected_revision':1,'utc_at':UTC.replace('+00:00','Z')},
        ):
            self.assertEqual(self.call(method='POST',body=bad)[0]
                             ['status'],'400 Bad Request')
        for raw in (b'{"request_id":"a","request_id":"b"}',b'[]',b'{'):
            self.assertEqual(self.call(method='POST',raw=raw)[0]['status'],
                             '400 Bad Request')
        self.assertEqual(self.service.calls,[])

    def test_failed_permission_and_untrusted_service_result(self):
        self.service.denied=True
        meta,data=self.call()
        self.assertEqual(meta['status'],'401 Unauthorized')
        self.assertNotIn('private account',str(data))
        self.service.denied=False
        self.service.unsafe=True
        for method in ('GET','POST','DELETE'):
            self.assertEqual(self.call(method=method)[0]['status'],
                             '503 Service Unavailable')
        with self.assertRaises(ValueError):
            BAMCalendarProposalsWSGI(self.service,enabled=1)

if __name__=='__main__':
    unittest.main()
