import json
import unittest
from bam_read_wsgi import BAMReadWSGI

class FakeReadAPI:
    def __init__(self):
        self.calls=[]
    def get_dashboard_view(self,*,session_token,server_now):
        self.calls.append(('dashboard',session_token,server_now))
        if session_token!='valid':
            raise PermissionError('denied')
        return {'schema_version':1,'tenant_id':'shop',
                'publishing_enabled':False}
    def list_held_drafts(self,*,session_token,server_now):
        self.calls.append(('drafts',session_token,server_now))
        if session_token!='valid':
            raise PermissionError('denied')
        return {'tenant_id':'shop','drafts':[],'publishing_enabled':False}
    def get_posting_preferences(self,*,session_token,server_now):
        self.calls.append(('preferences',session_token,server_now))
        if session_token!='valid':
            raise PermissionError('denied')
        return {'tenant_id':'shop','mode':'smart','configured':False,
                'publishing_enabled':False}

class BAMReadWSGITests(unittest.TestCase):
    def setUp(self):
        self.api=FakeReadAPI()
        self.app=BAMReadWSGI(self.api,clock=lambda:101)

    def request(self,path='/api/v1/dashboard',method='GET',
                token='valid',scheme='https'):
        captured={}
        def start(status,headers):
            captured['status']=status
            captured['headers']=dict(headers)
        env={'wsgi.url_scheme':scheme,'REQUEST_METHOD':method,
             'PATH_INFO':path}
        if token is not None:
            env['HTTP_AUTHORIZATION']='Bearer '+token
        result=b''.join(self.app(env,start))
        return captured,json.loads(result.decode('utf-8'))

    def test_dashboard_is_authenticated_and_uncacheable(self):
        meta,body=self.request()
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(body['tenant_id'],'shop')
        self.assertEqual(self.api.calls,[('dashboard','valid',101)])
        self.assertIn('no-store',meta['headers']['Cache-Control'])
        self.assertNotIn('Access-Control-Allow-Origin',meta['headers'])
        self.assertEqual(meta['headers']['X-Content-Type-Options'],'nosniff')

    def test_all_read_routes(self):
        for path,key in [('/api/v1/drafts','drafts'),
                         ('/api/v1/posting-preferences','mode')]:
            _,body=self.request(path)
            self.assertIn(key,body)

    def test_reject_insecure_transport_before_auth(self):
        meta,body=self.request(scheme='http')
        self.assertEqual(meta['status'],'403 Forbidden')
        self.assertEqual(self.api.calls,[])

    def test_reject_unauthorized_without_leakage(self):
        for token in ('invalid',None,''):
            meta,body=self.request(token=token)
            self.assertEqual(meta['status'],'401 Unauthorized')
            self.assertNotIn('invalid',str(body))

    def test_no_write_routes(self):
        meta,_=self.request(method='POST')
        self.assertEqual(meta['status'],'405 Method Not Allowed')
        self.assertEqual(self.api.calls,[])

    def test_unknown_route(self):
        meta,_=self.request(path='/api/v1/publish')
        self.assertEqual(meta['status'],'404 Not Found')
        self.assertEqual(self.api.calls,[])

    def test_internal_errors_hide_details(self):
        class Broken:
            def get_dashboard_view(self,**kwargs):
                raise RuntimeError('vault/private secret')
        app=BAMReadWSGI(Broken(),clock=lambda:101)
        captured={}
        result=b''.join(app({
            'wsgi.url_scheme':'https','REQUEST_METHOD':'GET',
            'PATH_INFO':'/api/v1/dashboard',
            'HTTP_AUTHORIZATION':'Bearer valid'
        },lambda status,headers:captured.update(status=status)))
        self.assertEqual(captured['status'],'503 Service Unavailable')
        self.assertNotIn(b'vault',result)

if __name__=='__main__':unittest.main()
