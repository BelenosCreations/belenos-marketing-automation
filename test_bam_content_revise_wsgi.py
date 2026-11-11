"""Strict one-component held draft revision HTTP boundary tests."""
import io
import json
import unittest

from bam_content_revise_wsgi import BAMContentReviseWSGI


class FakeAPI:
    def __init__(self):
        self.calls=[]
        self.denied=False
        self.stale=False
        self.unsafe=False

    def revise_held_draft(self,**kwargs):
        self.calls.append(kwargs)
        if self.denied:
            raise PermissionError('Denied privileged editing')
        if self.stale:
            raise ValueError('Stale draft revision')
        return {'tenant_id':'shop','request_id':kwargs['request_id'],
                'status':'needs_content',
                'revision':kwargs['expected_revision']+1,
                'publishing_enabled':self.unsafe}


class HeldRevisionWSGITests(unittest.TestCase):
    def setUp(self):
        self.api=FakeAPI()
        self.app=BAMContentReviseWSGI(self.api,enabled=True,clock=lambda:101)

    def call(self,*,app=None,body=None,raw=None,**changes):
        if raw is None:
            if body is None:
                body={'request_id':'a'*32,'target':'draft_text',
                      'revised_text':'Corrected product copy',
                      'expected_revision':1}
            raw=json.dumps(body).encode()
        env={'wsgi.url_scheme':'https','PATH_INFO':'/api/v1/content/drafts',
             'REQUEST_METHOD':'PUT','CONTENT_TYPE':'application/json',
             'CONTENT_LENGTH':str(len(raw)),'wsgi.input':io.BytesIO(raw),
             'HTTP_AUTHORIZATION':'Bearer '+'a'*43}
        env.update(changes)
        captured={}
        value=b''.join((app or self.app)(env,lambda status,headers:
            captured.update(status=status,headers=dict(headers))))
        return captured,json.loads(value)

    def test_valid_revision_only_unpublished(self):
        meta,value=self.call()
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(value['request_id'],'a'*32)
        self.assertEqual(value['revision'],2)
        self.assertFalse(value['publishing_enabled'])
        self.assertEqual(value['status'],'needs_content')
        self.assertEqual(meta['headers']['Cache-Control'],'no-store, private')
        self.assertEqual(self.api.calls[0]['target'],'draft_text')
        self.assertEqual(self.api.calls[0]['revised_text'],'Corrected product copy')
        meta,value=self.call(body={'request_id':'a'*32,
            'target':'suggestion','revised_text':'Corrected guidance',
            'expected_revision':2})
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(value['revision'],3)

    def test_disabled_insecure_method_or_role_claim(self):
        disabled=BAMContentReviseWSGI(self.api)
        self.assertEqual(self.call(app=disabled)[0]['status'],
                         '503 Service Unavailable')
        for changes,status in [
                ({'wsgi.url_scheme':'http',
                  'HTTP_X_FORWARDED_PROTO':'https'},'403 Forbidden'),
                ({'REQUEST_METHOD':'POST'},'405 Method Not Allowed'),
                ({'PATH_INFO':'/api/v1/publish'},'404 Not Found'),
                ({'HTTP_AUTHORIZATION':'Bearer short'},'401 Unauthorized'),
                ({'CONTENT_TYPE':'text/plain'},'400 Bad Request'),
                ({'CONTENT_LENGTH':'9999'},'400 Bad Request')]:
            self.assertEqual(self.call(**changes)[0]['status'],status)
        self.assertEqual(self.api.calls,[])

    def test_forged_claims_and_bad_revision_rejected(self):
        original={'request_id':'a'*32,'target':'draft_text',
                  'revised_text':'Correct copy','expected_revision':1}
        for extra in ('tenant_id','role','subject_id','publish_now','approved',
                      'schedule_at','image_id','required_items'):
            self.assertEqual(self.call(body={**original,
                extra:'forged'})[0]['status'],'400 Bad Request')
        for patch in ({'target':'publish'},
                      {'target':'status'},
                      {'request_id':'bad'},
                      {'expected_revision':0},
                      {'expected_revision':True},
                      {'revised_text':' '},
                      {'revised_text':'Bad whitespace '},
                      {'revised_text':'A'*2001}):
            self.assertEqual(self.call(body={**original,
                **patch})[0]['status'],'400 Bad Request')
        for raw in (b'{"target":"draft_text","target":"suggestion"}',
                    b'[]',b'{'):
            self.assertEqual(self.call(raw=raw)[0]['status'],
                             '400 Bad Request')
        self.assertEqual(self.api.calls,[])

    def test_stale_conflict_and_unsafe_result(self):
        self.api.stale=True
        meta,error=self.call()
        self.assertEqual(meta['status'],'409 Conflict')
        self.assertNotIn('Corrected product copy',str(error))
        self.api.stale=False
        self.api.unsafe=True
        self.assertEqual(self.call()[0]['status'],'503 Service Unavailable')
        self.api.denied=True
        self.assertEqual(self.call()[0]['status'],'401 Unauthorized')
        with self.assertRaises(ValueError):
            BAMContentReviseWSGI(self.api,enabled=1)


if __name__=='__main__':
    unittest.main()
