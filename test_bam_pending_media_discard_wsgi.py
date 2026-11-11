"""Private pending-only media removal transport regression tests."""
import io
import json
import unittest
from bam_pending_media_discard_wsgi import BAMPendingMediaDiscardWSGI

class FakeStore:
    def __init__(self):
        self.calls=[]
        self.denied=False
        self.invalid=False
    def discard(self,**kwargs):
        self.calls.append(kwargs)
        if self.denied:raise PermissionError('Wrong tenant')
        return {'tenant_id':'shop','request_id':kwargs['request_id'],
            'item':kwargs['item'],'removed':1,
            'media_verified':False,
            'publishing_enabled':self.invalid}

class MediaDiscardTests(unittest.TestCase):
    def setUp(self):
        self.store=FakeStore()
        self.app=BAMPendingMediaDiscardWSGI(
            self.store,enabled=True,clock=lambda:101)
    def call(self,*,app=None,body=None,raw=None,**updates):
        if raw is None:
            if body is None:
                body={'request_id':'a'*32,'item':'image'}
            raw=json.dumps(body).encode()
        env={'wsgi.url_scheme':'https',
             'PATH_INFO':'/api/v1/content/media-pending',
             'REQUEST_METHOD':'DELETE',
             'CONTENT_TYPE':'application/json',
             'CONTENT_LENGTH':str(len(raw)),
             'wsgi.input':io.BytesIO(raw),
             'HTTP_AUTHORIZATION':'Bearer '+'t'*43}
        env.update(updates)
        result={}
        payload=b''.join((app or self.app)(env,lambda status,headers:
            result.update(status=status,headers=dict(headers))))
        return result,json.loads(payload)
    def test_pending_only_discard(self):
        meta,body=self.call()
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(body['removed'],1)
        self.assertFalse(body['media_verified'])
        self.assertFalse(body['publishing_enabled'])
        self.assertEqual(meta['headers']['Cache-Control'],'no-store, private')
        self.assertEqual(self.store.calls[0]['token'],'t'*43)
    def test_fail_closed_and_private(self):
        self.assertEqual(self.call(app=BAMPendingMediaDiscardWSGI())[0]['status'],
                         '503 Service Unavailable')
        self.store.denied=True
        self.assertEqual(self.call()[0]['status'],'401 Unauthorized')
        self.store.denied=False
        self.store.invalid=True
        self.assertEqual(self.call()[0]['status'],'503 Service Unavailable')
        with self.assertRaises(ValueError):
            BAMPendingMediaDiscardWSGI(self.store,enabled=1)
    def test_reject_claims_methods_and_bad_body(self):
        for fields in [
            {'tenant_id':'other'}, {'attachment_id':'b'*32},
            {'role':'owner'}, {'publish_now':True},
            {'verified':True}]:
            meta,_=self.call(body={
                'request_id':'a'*32,'item':'image',**fields})
            self.assertEqual(meta['status'],'400 Bad Request')
        for bad in [
            b'{"item":"image","item":"photo"}',b'[]',b'{']:
            self.assertEqual(self.call(raw=bad)[0]['status'],'400 Bad Request')
        for changes,expected in [
            ({'wsgi.url_scheme':'http'},'403 Forbidden'),
            ({'PATH_INFO':'/api/v1/publish'},'404 Not Found'),
            ({'REQUEST_METHOD':'PUT'},'405 Method Not Allowed'),
            ({'HTTP_AUTHORIZATION':'Bearer invalid'},'401 Unauthorized'),
            ({'CONTENT_TYPE':'text/plain'},'400 Bad Request')]:
            self.assertEqual(self.call(**changes)[0]['status'],expected)

if __name__=='__main__':
    unittest.main()
