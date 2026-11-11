import json
import sqlite3
import unittest
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from business_curation import BusinessCuration
from business_switcher import BusinessSwitcher
from provider_connection_registry import ProviderConnectionRegistry
from social_connection_directory import SocialConnectionDirectory
from account_dashboard import AccountDashboard
from account_read_api import AccountReadAPI
from posting_preferences import PostingPreferences
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
    def get_ai_cost_summary(self,*,session_token,server_now):
        self.calls.append(('ai_cost',session_token,server_now))
        if session_token!='valid':
            raise PermissionError('denied')
        return {'tenant_id':'shop','events':0,'input_tokens':0,
                'output_tokens':0,'estimated_micro_usd':0,
                'pricing_basis':'operator_configured',
                'actual_billing_verified':False,
                'publishing_enabled':False}
    def get_ai_business_facts(self,*,session_token,server_now):
        self.calls.append(('ai_facts',session_token,server_now))
        if session_token!='valid':
            raise PermissionError('denied')
        return {'tenant_id':'shop','facts':{},'revision':0,
                'provenance':'not_configured','confirmed_at':None,
                'publishing_enabled':False}
    def get_ai_settings(self,*,session_token,server_now):
        self.calls.append(('ai_settings',session_token,server_now))
        if session_token!='valid':
            raise PermissionError('denied')
        return {'tenant_id':'shop','provider':'openai',
                'mode':'bam_sponsored','own_key_configured':False,
                'memory':{},'key_exposed':False,
                'publishing_enabled':False}
    def list_ai_content_drafts(self,*,session_token,server_now):
        self.calls.append(('ai_drafts',session_token,server_now))
        if session_token!='valid':
            raise PermissionError('denied')
        return {'tenant_id':'shop','drafts':[],
                'publishing_enabled':False}
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
                         ('/api/v1/posting-preferences','mode'),
                         ('/api/v1/ai-drafts','drafts'),
                         ('/api/v1/ai-settings','mode'),
                         ('/api/v1/ai-business-facts','facts'),
                         ('/api/v1/ai-cost-summary','events')]:
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

class BAMReadWSGIIntegrationTests(unittest.TestCase):
    def test_real_authenticated_dashboard_and_business_switch_isolation(self):
        db=sqlite3.connect(':memory:')
        try:
            directory=AccountDirectory(db)
            directory.bootstrap_owner('shop','owner')
            directory.bootstrap_owner('other','other_owner')
            directory.set_member(Principal('other_owner','other',Role.OWNER),
                                 'owner',Role.VIEWER)
            sessions=SessionStore(db)
            token=sessions.issue(Principal('owner','shop',Role.OWNER),now=100)
            curation=BusinessCuration(db)
            curation.create_profile('shop','Main Shop','retail',['retail'])
            curation.create_profile('other','Other Shop','service',['service'])
            registry=ProviderConnectionRegistry(db)
            registry.register_trusted(tenant_id='shop',platform='facebook',
                account_id='shop_page',vault_reference='vault/private',
                scope='read_insights',state='connected',expires_at=1000,now=100)
            switcher=BusinessSwitcher(db,sessions,directory)
            social=SocialConnectionDirectory(registry=registry,
                directory=directory,sessions=sessions)
            dashboard=AccountDashboard(sessions=sessions,directory=directory,
                switcher=switcher,social_connections=social)
            api=AccountReadAPI(dashboard,posting_preferences=PostingPreferences(
                db=db,sessions=sessions,directory=directory))
            app=BAMReadWSGI(api,clock=lambda:101)
            def get(t):
                status={}
                data=b''.join(app({'wsgi.url_scheme':'https',
                    'REQUEST_METHOD':'GET','PATH_INFO':'/api/v1/dashboard',
                    'HTTP_AUTHORIZATION':'Bearer '+t},
                    lambda code,headers:status.update(code=code)))
                return status['code'],json.loads(data)
            code,body=get(token)
            self.assertEqual(code,'200 OK')
            self.assertEqual(body['tenant_id'],'shop')
            self.assertEqual(body['cards'][3]['value'],1)
            self.assertNotIn('vault/',str(body))
            switched=api.activate_business(session_token=token,
                target_tenant_id='other',server_now=101)
            code,other=get(switched['session_token'])
            self.assertEqual(code,'200 OK')
            self.assertEqual(other['tenant_id'],'other')
            self.assertIsNone(other['cards'][3]['value'])
            self.assertEqual(other['cards'][3]['availability'],'restricted')
            self.assertNotIn('shop_page',str(other))
            self.assertFalse(other['publishing_enabled'])
        finally:
            db.close()

if __name__=='__main__':unittest.main()
