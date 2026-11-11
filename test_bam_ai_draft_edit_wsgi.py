"""Strict manual single-component draft editor WSGI boundary tests."""
import io
import json
import unittest
from bam_ai_draft_edit_wsgi import BAMAIDraftEditWSGI

class DraftService:
    def __init__(self):
        self.calls=[]
        self.denied=False
    def edit_ai_draft_component(self,**kwargs):
        self.calls.append(kwargs)
        if self.denied:
            raise PermissionError('No role')
        return {'tenant_id':'shop','draft_id':kwargs['draft_id'],
            'platform':'facebook',
            'post_text':kwargs['revised_text'] if kwargs['target']=='post_text'
                  else 'Existing copy',
            'image_prompt':kwargs['revised_text'] if kwargs['target']=='image_prompt'
                    else 'Existing conceptual image',
            'needs_media':True,'media_attached':False,'status':'needs_media',
            'revision':kwargs['expected_revision']+1,
            'publishing_enabled':False}

class ManualEditWSGITests(unittest.TestCase):
    def setUp(self):
        self.api=DraftService()
        self.app=BAMAIDraftEditWSGI(self.api,enabled=True,clock=lambda:101)
    def call(self,*,app=None,body=None,raw=None,**extra):
        if raw is None:
            if body is None:
                body={'draft_id':'a'*32,'target':'post_text',
                      'revised_text':'New copy','expected_revision':1}
            raw=json.dumps(body).encode()
        env={'wsgi.url_scheme':'https','PATH_INFO':'/api/v1/ai-drafts',
             'REQUEST_METHOD':'PUT','CONTENT_TYPE':'application/json',
             'CONTENT_LENGTH':str(len(raw)),'wsgi.input':io.BytesIO(raw),
             'HTTP_AUTHORIZATION':'Bearer '+'a'*43}
        env.update(extra)
        got={}
        data=b''.join((app or self.app)(env,lambda status,headers:
            got.update(status=status,headers=dict(headers))))
        return got,json.loads(data)

    def test_only_target_component_can_change(self):
        meta,data=self.call()
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(data['post_text'],'New copy')
        self.assertEqual(data['image_prompt'],'Existing conceptual image')
        self.assertFalse(data['publishing_enabled'])
        self.assertEqual(data['revision'],2)
        self.assertEqual(meta['headers']['Cache-Control'],'no-store, private')
        _,changed=self.call(body={'draft_id':'a'*32,
            'target':'image_prompt','revised_text':'Different image',
            'expected_revision':2})
        self.assertEqual(changed['image_prompt'],'Different image')
        self.assertEqual(changed['post_text'],'Existing copy')

    def test_disabled_wrong_method_and_https(self):
        self.assertEqual(self.call(app=BAMAIDraftEditWSGI(self.api))[0]['status'],
                         '503 Service Unavailable')
        for k,status in [
                ({'REQUEST_METHOD':'POST'},'405 Method Not Allowed'),
                ({'PATH_INFO':'/api/v1/publish'},'404 Not Found'),
                ({'wsgi.url_scheme':'http',
                  'HTTP_X_FORWARDED_PROTO':'https'},'403 Forbidden'),
                ({'HTTP_AUTHORIZATION':'Bearer no'},'401 Unauthorized'),
                ({'CONTENT_TYPE':'text/plain'},'400 Bad Request'),
                ({'CONTENT_LENGTH':'30000'},'400 Bad Request')]:
            self.assertEqual(self.call(**k)[0]['status'],status)
        self.assertEqual(self.api.calls,[])

    def test_rejects_claims_invalid_and_duplicates(self):
        base={'draft_id':'a'*32,'target':'post_text',
              'revised_text':'Copy','expected_revision':1}
        for key in ('tenant_id','role','subject_id','publish',
                    'approved','schedule_at','image_prompt'):
            self.assertEqual(self.call(body={**base,key:'forged'})[0]['status'],
                             '400 Bad Request')
        for patch in ({'target':'publish'},{'target':'post_text','revised_text':''},
                      {'target':'image_prompt','revised_text':'X'*2001},
                      {'draft_id':'wrong'},{'expected_revision':0},
                      {'expected_revision':True},{'revised_text':7}):
            self.assertEqual(self.call(body={**base,**patch})[0]['status'],
                             '400 Bad Request')
        for raw in (
                b'{"target":"post_text","target":"image_prompt"}',
                b'[]',b'{'):
            self.assertEqual(self.call(raw=raw)[0]['status'],
                             '400 Bad Request')
        self.assertEqual(self.api.calls,[])

    def test_denial_does_not_echo_private_error(self):
        self.api.denied=True
        meta,data=self.call()
        self.assertEqual(meta['status'],'401 Unauthorized')
        self.assertNotIn('No role',str(data))

    def test_untrusted_success_response_rejected(self):
        class Bad(DraftService):
            def edit_ai_draft_component(self,**kwargs):
                item=super().edit_ai_draft_component(**kwargs)
                item['publishing_enabled']=True
                return item
        self.assertEqual(self.call(app=BAMAIDraftEditWSGI(
            Bad(),enabled=True,clock=lambda:101))[0]['status'],
            '503 Service Unavailable')

if __name__=='__main__':
    unittest.main()
