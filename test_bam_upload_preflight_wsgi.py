"""No-upload attachment metadata preflight boundary."""
import io
import json
import unittest

from bam_upload_preflight_wsgi import BAMUploadPreflightWSGI

class FakePreflight:
    def __init__(self):
        self.calls=[]
        self.denied=False
    def begin_content_upload_preflight(self,**kwargs):
        self.calls.append(kwargs)
        if self.denied:
            raise PermissionError('Role denied')
        return {'tenant_id':'shop','request_id':kwargs['request_id'],
            'item':kwargs['item'],'attachment_id':'b'*32,
            'status':'pending','upload_url':None,
            'max_bytes':20*1024*1024,'publishing_enabled':False}

class PreflightWSGITests(unittest.TestCase):
    def setUp(self):
        self.api=FakePreflight()
        self.app=BAMUploadPreflightWSGI(
            self.api,enabled=True,clock=lambda:101)
    def call(self,*,app=None,body=None,raw=None,**overrides):
        if raw is None:
            if body is None:
                body={'request_id':'a'*32,'item':'image',
                    'media_type':'image/png','sha256':'f'*64,
                    'byte_count':1024}
            raw=json.dumps(body).encode('utf-8')
        env={'wsgi.url_scheme':'https',
             'PATH_INFO':'/api/v1/content/upload-preflight',
             'REQUEST_METHOD':'POST',
             'CONTENT_TYPE':'application/json',
             'CONTENT_LENGTH':str(len(raw)),
             'wsgi.input':io.BytesIO(raw),
             'HTTP_AUTHORIZATION':'Bearer '+'a'*43}
        env.update(overrides)
        meta={}
        body=b''.join((app or self.app)(env,lambda status,headers:
            meta.update(status=status,headers=dict(headers))))
        return meta,json.loads(body)
    def test_accepted_only_as_pending_without_upload_access(self):
        meta,result=self.call()
        self.assertEqual(meta['status'],'202 Accepted')
        self.assertEqual(result['status'],'pending')
        self.assertIsNone(result['upload_url'])
        self.assertFalse(result['publishing_enabled'])
        self.assertEqual(meta['headers']['Cache-Control'],'no-store, private')
        self.assertNotIn('storage_key',result)
        self.assertEqual(self.api.calls[0]['byte_count'],1024)
    def test_disabled_http_wrong_method_and_auth(self):
        self.assertEqual(self.call(app=BAMUploadPreflightWSGI(self.api))[0]
                         ['status'],'503 Service Unavailable')
        for override,expected in [
            ({'wsgi.url_scheme':'http',
              'HTTP_X_FORWARDED_PROTO':'https'},'403 Forbidden'),
            ({'REQUEST_METHOD':'GET'},'405 Method Not Allowed'),
            ({'PATH_INFO':'/api/v1/content/publish'},'404 Not Found'),
            ({'HTTP_AUTHORIZATION':'Bearer invalid'},'401 Unauthorized'),
            ({'CONTENT_TYPE':'multipart/form-data'},'400 Bad Request'),
            ({'CONTENT_LENGTH':'9999'},'400 Bad Request')]:
            self.assertEqual(self.call(**override)[0]['status'],expected)
        self.assertEqual(self.api.calls,[])
    def test_claims_bytes_and_malformed_body_rejected(self):
        basic={'request_id':'a'*32,'item':'image',
               'media_type':'image/png','sha256':'f'*64,'byte_count':100}
        for add in ('tenant_id','role','storage_key','upload_url',
                    'verified','publish_now','attachment_id','content'):
            self.assertEqual(self.call(body={**basic,add:'forged'})[0]
                             ['status'],'400 Bad Request')
        for modified in [
                {'request_id':'wrong'},
                {'sha256':'f'*63},
                {'byte_count':True},
                {'byte_count':0},
                {'byte_count':21*1024*1024},
                {'media_type':'application/x-executable'},
                {'item':''}]:
            self.assertEqual(self.call(body={**basic,**modified})[0]
                             ['status'],'400 Bad Request')
        for raw in (
                b'{"request_id":"a","request_id":"b"}',b'[]',b'{'):
            self.assertEqual(self.call(raw=raw)[0]['status'],
                             '400 Bad Request')
        self.assertEqual(self.api.calls,[])
    def test_rejected_permissions(self):
        self.api.denied=True
        meta,result=self.call()
        self.assertEqual(meta['status'],'401 Unauthorized')
        self.assertNotIn('Role denied',str(result))
    def test_trusted_scope_cannot_change(self):
        class Bad(FakePreflight):
            def begin_content_upload_preflight(self,**kwargs):
                result=super().begin_content_upload_preflight(**kwargs)
                result['item']='other'
                return result
        app=BAMUploadPreflightWSGI(Bad(),enabled=True,clock=lambda:101)
        self.assertEqual(self.call(app=app)[0]['status'],
                         '503 Service Unavailable')
    def test_boolean_enable_required(self):
        with self.assertRaises(ValueError):
            BAMUploadPreflightWSGI(self.api,enabled='yes')
if __name__=='__main__':
    unittest.main()
