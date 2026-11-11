"""No unverified image receipt can approve media or publish a post."""
import io
import json
import unittest
from bam_pending_media_wsgi import BAMPendingMediaWSGI

PNG=b'\x89PNG\r\n\x1a\n'+b'png-test-bytes'

class FakeStore:
    def __init__(self):
        self.calls=[]
        self.denied=False
    def authorize_slot(self,*,token,attachment_id,now):
        if self.denied:raise PermissionError('Role denied')
        return {'tenant_id':'shop','attachment_id':attachment_id,
            'media_type':'image/png','max_bytes':20*1024*1024}
    def receive(self,**kwargs):
        self.calls.append(kwargs)
        return {'tenant_id':'shop','attachment_id':kwargs['attachment_id'],
            'status':'pending_scan','bytes_received':len(kwargs['content']),
            'media_verified':False,'publishing_enabled':False}

class PendingMediaWSGITests(unittest.TestCase):
    def setUp(self):
        self.store=FakeStore()
        self.app=BAMPendingMediaWSGI(self.store,enabled=True,clock=lambda:101)
    def call(self,*,app=None,raw=PNG,**override):
        env={'wsgi.url_scheme':'https',
             'PATH_INFO':'/api/v1/content/media-bytes',
             'REQUEST_METHOD':'PUT',
             'CONTENT_TYPE':'image/png',
             'CONTENT_LENGTH':str(len(raw)),
             'wsgi.input':io.BytesIO(raw),
             'HTTP_X_BAM_ATTACHMENT_ID':'b'*32,
             'HTTP_AUTHORIZATION':'Bearer '+'a'*43}
        env.update(override)
        got={}
        data=b''.join((app or self.app)(env,lambda status,headers:
            got.update(status=status,headers=dict(headers))))
        return got,json.loads(data)
    def test_pending_receipt_accepted_and_safe(self):
        meta,result=self.call()
        self.assertEqual(meta['status'],'202 Accepted')
        self.assertEqual(result['status'],'pending_scan')
        self.assertFalse(result['media_verified'])
        self.assertFalse(result['publishing_enabled'])
        self.assertEqual(self.store.calls[0]['content'],PNG)
        self.assertEqual(meta['headers']['Cache-Control'],'no-store, private')
        self.assertNotIn('storage_key',result)
    def test_disabled_unsafe_method_and_untrusted_content(self):
        self.assertEqual(self.call(app=BAMPendingMediaWSGI())[0]['status'],
                         '503 Service Unavailable')
        for opts,status in [
            ({'wsgi.url_scheme':'http',
              'HTTP_X_FORWARDED_PROTO':'https'},'403 Forbidden'),
            ({'REQUEST_METHOD':'GET'},'405 Method Not Allowed'),
            ({'PATH_INFO':'/api/v1/publish'},'404 Not Found'),
            ({'HTTP_AUTHORIZATION':'Bearer invalid'},'401 Unauthorized'),
            ({'HTTP_X_BAM_ATTACHMENT_ID':'wrong'},'400 Bad Request'),
            ({'CONTENT_TYPE':'application/octet-stream'},'400 Bad Request'),
            ({'CONTENT_LENGTH':'0'},'400 Bad Request'),
            ({'CONTENT_LENGTH':str(21*1024*1024)},'400 Bad Request')
        ]:
            with self.subTest(opts=opts):
                self.assertEqual(self.call(**opts)[0]['status'],status)
        self.assertEqual(self.store.calls,[])
    def test_denied_and_incomplete_upload(self):
        self.store.denied=True
        self.assertEqual(self.call()[0]['status'],'401 Unauthorized')
        self.store.denied=False
        self.assertEqual(self.call(CONTENT_LENGTH='1234')[0]['status'],
                         '400 Bad Request')
        self.assertEqual(self.store.calls,[])
    def test_no_forged_verification_in_success_result(self):
        class Bad(FakeStore):
            def receive(self,**kwargs):
                result=super().receive(**kwargs)
                result['media_verified']=True
                return result
        app=BAMPendingMediaWSGI(Bad(),enabled=True,clock=lambda:101)
        self.assertEqual(self.call(app=app)[0]['status'],
                         '503 Service Unavailable')
        with self.assertRaises(ValueError):
            BAMPendingMediaWSGI(self.store,enabled=1)

if __name__=='__main__':unittest.main()
