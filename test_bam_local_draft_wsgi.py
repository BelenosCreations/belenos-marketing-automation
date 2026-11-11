"""Unpaid local product draft generation transport tests."""
import io
import json
import unittest

from bam_local_draft_wsgi import BAMLocalProductDraftWSGI

class FakeDrafts:
    def __init__(self):
        self.calls=[]
        self.denied=False
    def create_local_product_draft(self,**kwargs):
        self.calls.append(kwargs)
        if self.denied:raise PermissionError('Forbidden')
        image='Generic marketing concept' if kwargs['include_image_prompt'] else None
        return {'tenant_id':'shop','draft_id':'b'*32,
            'platform':kwargs['platform'],
            'post_text':'Example Shop: Custom tumblers. Contact us for details.',
            'image_prompt':image,
            'needs_media':kwargs['include_image_prompt'],
            'media_attached':False,
            'status':'needs_media' if image else 'draft_pending_verification',
            'revision':1,'publishing_enabled':False,
            'generation_method':'local_template','openai_requests':0}

class LocalDraftWSGITests(unittest.TestCase):
    def setUp(self):
        self.api=FakeDrafts()
        self.app=BAMLocalProductDraftWSGI(self.api,enabled=True,clock=lambda:101)
    def call(self,*,app=None,body=None,raw=None,**overrides):
        if raw is None:
            if body is None:body={'platform':'facebook',
                                  'include_image_prompt':True}
            raw=json.dumps(body).encode('utf-8')
        env={'wsgi.url_scheme':'https',
             'PATH_INFO':'/api/v1/ai/local-product-draft',
             'REQUEST_METHOD':'POST',
             'CONTENT_TYPE':'application/json',
             'CONTENT_LENGTH':str(len(raw)),
             'wsgi.input':io.BytesIO(raw),
             'HTTP_AUTHORIZATION':'Bearer '+'a'*43}
        env.update(overrides)
        meta={}
        text=b''.join((app or self.app)(env,lambda status,headers:
            meta.update(status=status,headers=dict(headers))))
        return meta,json.loads(text)
    def test_explicit_draft_with_optional_manual_image_prompt(self):
        meta,result=self.call()
        self.assertEqual(meta['status'],'201 Created')
        self.assertEqual(result['status'],'needs_media')
        self.assertEqual(result['generation_method'],'local_template')
        self.assertEqual(result['openai_requests'],0)
        self.assertFalse(result['publishing_enabled'])
        self.assertFalse(result['media_attached'])
        self.assertEqual(meta['headers']['Cache-Control'],'no-store, private')
        meta,other=self.call(body={'platform':'instagram',
                                   'include_image_prompt':False})
        self.assertEqual(meta['status'],'201 Created')
        self.assertIsNone(other['image_prompt'])
        self.assertEqual(other['status'],'draft_pending_verification')
    def test_disabled_untrusted_transport_and_claims(self):
        self.assertEqual(self.call(app=BAMLocalProductDraftWSGI(self.api))[0]
                         ['status'],'503 Service Unavailable')
        for override,expected in [
            ({'wsgi.url_scheme':'http',
              'HTTP_X_FORWARDED_PROTO':'https'},'403 Forbidden'),
            ({'PATH_INFO':'/api/v1/ai/publish'},'404 Not Found'),
            ({'REQUEST_METHOD':'GET'},'405 Method Not Allowed'),
            ({'CONTENT_TYPE':'text/plain'},'400 Bad Request'),
            ({'CONTENT_LENGTH':'900'},'400 Bad Request'),
            ({'HTTP_AUTHORIZATION':'Bearer invalid'},'401 Unauthorized')]:
            self.assertEqual(self.call(**override)[0]['status'],expected)
        self.assertEqual(self.api.calls,[])
    def test_no_client_tenant_fact_claim_or_paid_generation(self):
        for bad in [
            {'platform':'facebook','include_image_prompt':True,
             'tenant_id':'other'},
            {'platform':'facebook','include_image_prompt':True,
             'role':'owner'},
            {'platform':'facebook','include_image_prompt':True,
             'facts':{'business_name':'Fake'}},
            {'platform':'facebook','include_image_prompt':True,
             'model':'expensive'},
            {'platform':'facebook','include_image_prompt':True,
             'publish_now':True},
            {'platform':'facebook','include_image_prompt':1},
            {'platform':'facebook','include_image_prompt':'true'},
            {'platform':'bad','include_image_prompt':False}]:
            self.assertEqual(self.call(body=bad)[0]['status'],
                             '400 Bad Request')
        for raw in (b'{"platform":"facebook","platform":"instagram"}',
                    b'[]',b'{'):
            self.assertEqual(self.call(raw=raw)[0]['status'],
                             '400 Bad Request')
        self.assertEqual(self.api.calls,[])
    def test_denial_and_unsafe_result_fail_closed(self):
        self.api.denied=True
        meta,result=self.call()
        self.assertEqual(meta['status'],'401 Unauthorized')
        self.assertNotIn('Forbidden',str(result))
        class Unsafe(FakeDrafts):
            def create_local_product_draft(self,**kwargs):
                res=super().create_local_product_draft(**kwargs)
                res['publishing_enabled']=True
                return res
        app=BAMLocalProductDraftWSGI(Unsafe(),enabled=True,clock=lambda:101)
        self.assertEqual(self.call(app=app)[0]['status'],
                         '503 Service Unavailable')
    def test_service_route_is_separate_and_pending_only(self):
        class Service(FakeDrafts):
            def create_local_service_draft(self,**kwargs):
                result=self.create_local_product_draft(**kwargs)
                result['post_text']='Example Services: Facility cleaning. Contact us for details.'
                return result
        service=Service()
        app=BAMLocalProductDraftWSGI(
            service,enabled=True,clock=lambda:101,template='service')
        meta,data=self.call(app=app,
            PATH_INFO='/api/v1/ai/local-service-draft')
        self.assertEqual(meta['status'],'201 Created')
        self.assertIn('Facility cleaning',data['post_text'])
        self.assertEqual(data['openai_requests'],0)
        self.assertFalse(data['publishing_enabled'])
        self.assertEqual(self.call(app=app)[0]['status'],'404 Not Found')
        with self.assertRaises(ValueError):
            BAMLocalProductDraftWSGI(service,template='publish')

    def test_boolean_enable_required(self):
        with self.assertRaises(ValueError):
            BAMLocalProductDraftWSGI(self.api,enabled=1)
if __name__=='__main__':
    unittest.main()
