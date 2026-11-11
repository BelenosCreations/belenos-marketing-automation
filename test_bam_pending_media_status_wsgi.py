"""Verify no private data or approval in pending media status."""
import json
import unittest
from bam_pending_media_status_wsgi import BAMPendingMediaStatusWSGI

class FakeStore:
    def __init__(self):
        self.denied=False
        self.calls=[]
        self.extra=False
    def statuses(self,**kwargs):
        self.calls.append(kwargs)
        if self.denied:
            raise PermissionError('No access')
        item={'request_id':'a'*32,'item':'image','status':'pending_scan'}
        if self.extra:item['storage_key']='secret'
        return {'tenant_id':'shop','items':[item],
            'media_verified':False,'publishing_enabled':False}

class StatusTransportTests(unittest.TestCase):
    def setUp(self):
        self.store=FakeStore()
        self.app=BAMPendingMediaStatusWSGI(
            self.store,enabled=True,clock=lambda:101)
    def call(self,*,app=None,**changes):
        env={'wsgi.url_scheme':'https',
             'PATH_INFO':'/api/v1/content/media-status',
             'REQUEST_METHOD':'GET',
             'HTTP_AUTHORIZATION':'Bearer '+'t'*43}
        env.update(changes)
        result={}
        raw=b''.join((app or self.app)(env,lambda status,headers:
            result.update(status=status,headers=dict(headers))))
        return result,json.loads(raw)
    def test_valid_private_status(self):
        meta,result=self.call()
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(result['items'][0]['status'],'pending_scan')
        self.assertFalse(result['media_verified'])
        self.assertFalse(result['publishing_enabled'])
        self.assertEqual(meta['headers']['Cache-Control'],'no-store, private')
        self.assertEqual(self.store.calls,[{'token':'t'*43,'now':101}])
    def test_fail_closed(self):
        self.assertEqual(self.call(app=BAMPendingMediaStatusWSGI())[0]
                         ['status'],'503 Service Unavailable')
        self.store.denied=True
        self.assertEqual(self.call()[0]['status'],'401 Unauthorized')
        self.store.denied=False
        self.store.extra=True
        self.assertEqual(self.call()[0]['status'],'503 Service Unavailable')
    def test_invalid_transport(self):
        for change,status in [
                ({'wsgi.url_scheme':'http',
                  'HTTP_X_FORWARDED_PROTO':'https'},'403 Forbidden'),
                ({'PATH_INFO':'/api/v1/publish'},'404 Not Found'),
                ({'REQUEST_METHOD':'POST'},'405 Method Not Allowed'),
                ({'QUERY_STRING':'tenant_id=other'},'400 Bad Request'),
                ({'HTTP_AUTHORIZATION':'Bearer wrong'},'401 Unauthorized')]:
            with self.subTest(change=change):
                self.assertEqual(self.call(**change)[0]['status'],status)
        with self.assertRaises(ValueError):
            BAMPendingMediaStatusWSGI(self.store,enabled=1)

if __name__=='__main__':
    unittest.main()
