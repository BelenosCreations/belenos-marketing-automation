"""Security tests for the unpublished content mutation gateway."""
import io
import json
import unittest

from bam_content_write_wsgi import BAMContentWriteWSGI


class FakeContentAPI:
    def __init__(self):
        self.calls=[]
        self.blocked=False

    def create_held_draft(self,**kwargs):
        self.calls.append(('create',kwargs))
        if self.blocked:
            raise PermissionError('Viewer cannot create')
        return {'tenant_id':'shop','request_id':'a'*32,
                'status':'needs_content','publishing_enabled':False}

    def update_draft_hold(self,**kwargs):
        self.calls.append(('hold',kwargs))
        if self.blocked:
            raise PermissionError('Viewer cannot edit')
        return {'tenant_id':'shop','request_id':kwargs['request_id'],
                'status':kwargs['status'],'publishing_enabled':False}


class BAMContentWriteWSGITests(unittest.TestCase):
    def setUp(self):
        self.api=FakeContentAPI()
        self.app=BAMContentWriteWSGI(
            self.api,enabled=True,clock=lambda:101)

    def call(self,*,app=None,path='/api/v1/content/drafts',
             body=None,raw=None,**changes):
        if raw is None:
            if body is None:
                body={'channel':'facebook','draft_text':'Product preview',
                      'suggestion':'Verify the image before approval',
                      'required_items':['image']}
            raw=json.dumps(body).encode('utf-8')
        env={'wsgi.url_scheme':'https','PATH_INFO':path,
             'REQUEST_METHOD':'POST',
             'HTTP_AUTHORIZATION':'Bearer '+'a'*43,
             'CONTENT_TYPE':'application/json',
             'CONTENT_LENGTH':str(len(raw)),
             'wsgi.input':io.BytesIO(raw)}
        env.update(changes)
        got={}
        result=b''.join((app or self.app)(env,lambda status,headers:
            got.update(status=status,headers=dict(headers))))
        return got,json.loads(result)

    def test_default_disabled_and_create_held_only(self):
        off=BAMContentWriteWSGI(self.api)
        self.assertEqual(self.call(app=off)[0]['status'],
                         '503 Service Unavailable')
        self.assertEqual(self.api.calls,[])
        meta,result=self.call()
        self.assertEqual(meta['status'],'201 Created')
        self.assertEqual(result['status'],'needs_content')
        self.assertFalse(result['publishing_enabled'])
        self.assertNotIn('draft_text',result)
        self.assertEqual(meta['headers']['Cache-Control'],'no-store, private')
        self.assertEqual(self.api.calls[0][1]['required_items'],['image'])

    def test_hold_postponed_and_reopened(self):
        for state in ('postponed','needs_content','unavailable'):
            meta,result=self.call(path='/api/v1/content/hold',
                body={'request_id':'a'*32,'status':state})
            self.assertEqual(meta['status'],'200 OK')
            self.assertEqual(result['status'],state)
        self.assertEqual([name for name,_ in self.api.calls],
                         ['hold']*3)

    def test_client_cannot_claim_tenant_role_or_publish(self):
        sample={'channel':'facebook','draft_text':'Product preview',
                'suggestion':'Verify','required_items':['image']}
        for field in ('tenant_id','role','publishing_enabled','schedule_at'):
            with self.subTest(field=field):
                meta,_=self.call(body={**sample,field:'owner'})
                self.assertEqual(meta['status'],'400 Bad Request')
        self.assertEqual(self.api.calls,[])

    def test_no_unverified_media_or_published_state(self):
        for body in ({'request_id':'a'*32,'status':'published'},
                     {'request_id':'a'*32,'status':'approved'},
                     {'request_id':'a'*32,'status':'needs_content',
                      'attachment_id':'b'*32}):
            with self.subTest(body=body):
                meta,_=self.call(path='/api/v1/content/hold',body=body)
                self.assertEqual(meta['status'],'400 Bad Request')
        self.assertEqual(self.api.calls,[])

    def test_duplicate_json_fields_and_malformed_json(self):
        for raw in (b'{"channel":"facebook","channel":"instagram"}',
                    b'{','[]',b'null'):
            with self.subTest(raw=raw):
                meta,_=self.call(raw=raw)
                self.assertEqual(meta['status'],'400 Bad Request')
        self.assertEqual(self.api.calls,[])

    def test_permission_rejection_and_errors_are_generic(self):
        self.api.blocked=True
        meta,result=self.call()
        self.assertEqual(meta['status'],'401 Unauthorized')
        self.assertNotIn('Viewer',str(result))

    def test_https_auth_size_and_method_boundary(self):
        for change,expected in [
            ({'wsgi.url_scheme':'http',
              'HTTP_X_FORWARDED_PROTO':'https'},'403 Forbidden'),
            ({'HTTP_AUTHORIZATION':'Bearer invalid'},'401 Unauthorized'),
            ({'HTTP_AUTHORIZATION':'Bearer '+'a'*43+' '},'401 Unauthorized'),
            ({'CONTENT_LENGTH':'90000'},'400 Bad Request'),
            ({'CONTENT_TYPE':'text/plain'},'400 Bad Request'),
            ({'REQUEST_METHOD':'GET'},'405 Method Not Allowed'),
            ({'PATH_INFO':'/api/v1/post/publish'},'404 Not Found')]:
            with self.subTest(change=change):
                meta,_=self.call(**change)
                self.assertEqual(meta['status'],expected)
        self.assertEqual(self.api.calls,[])

    def test_non_boolean_enable_flag_rejected(self):
        with self.assertRaises(ValueError):
            BAMContentWriteWSGI(self.api,enabled=1)


if __name__=='__main__':
    unittest.main()
