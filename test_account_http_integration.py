"""End-to-end offline account HTTP test using actual BAM service classes."""
import http.client
import json
import sqlite3
import threading
import unittest

from access_policy import Principal, Role
from accounts import AccountDirectory
from account_dashboard import AccountDashboard
from account_read_api import AccountReadAPI
from business_curation import BusinessCuration
from business_switcher import BusinessSwitcher
from content_requests import ContentRequests
from content_request_service import ContentRequestService
from content_attachments import AttachmentRegistry
from dev_http_gateway import create_loopback_server
from provider_connection_registry import ProviderConnectionRegistry
from sessions import SessionStore
from social_connection_directory import SocialConnectionDirectory

class AccountHTTPIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:',check_same_thread=False)
        self.directory=AccountDirectory(self.db)
        self.directory.bootstrap_owner('retail','owner')
        self.directory.bootstrap_owner('cleaning','cleaner')
        self.directory.set_member(Principal('cleaner','cleaning',Role.OWNER),
                                  'owner',Role.CONTENT_CREATOR)
        profiles=BusinessCuration(self.db)
        profiles.create_profile('retail','Retail','retail',['products'])
        profiles.create_profile('cleaning','Cleaning','services',['commercial'])
        self.sessions=SessionStore(self.db)
        self.token=self.sessions.issue(Principal('owner','retail',Role.OWNER),now=100)
        registry=ProviderConnectionRegistry(self.db)
        registry.register_trusted(tenant_id='retail',platform='facebook',
            account_id='retail_page',vault_reference='vault/retail',
            scope='read_insights',state='connected',expires_at=2000,now=100)
        registry.register_trusted(tenant_id='cleaning',platform='instagram',
            account_id='cleaning_page',vault_reference='vault/cleaning',
            scope='read_insights',state='connected',expires_at=2000,now=100)
        requests=ContentRequests(self.db)
        content=ContentRequestService(requests=requests,sessions=self.sessions,
            directory=self.directory,attachments=AttachmentRegistry(self.db))
        dashboard=AccountDashboard(sessions=self.sessions,directory=self.directory,
            switcher=BusinessSwitcher(self.db,self.sessions,self.directory),
            social_connections=SocialConnectionDirectory(
                registry=registry,directory=self.directory,sessions=self.sessions),
            content_service=content)
        self.server=create_loopback_server(AccountReadAPI(dashboard),clock=lambda:101)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.db.close()

    def request(self,method,path,token,body=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'}
        payload=json.dumps(body).encode() if body is not None else None
        conn.request(method,path,body=payload,headers=headers)
        response=conn.getresponse()
        status=response.status
        result=json.loads(response.read())
        conn.close()
        return status,result

    def test_switch_restrict_logout_full_flow(self):
        status,initial=self.request('GET','/api/account/overview',self.token)
        self.assertEqual(status,200)
        self.assertEqual(initial['tenant_id'],'retail')
        self.assertEqual(initial['social_connections'][0]['platform'],'facebook')
        self.assertEqual(len(initial['businesses']),2)
        status,switched=self.request('POST','/api/account/activate',self.token,
                                    {'target_tenant_id':'cleaning'})
        self.assertEqual(status,200)
        self.assertEqual(switched['overview']['role'],'content_creator')
        self.assertIsNone(switched['overview']['social_connections'])
        target_token=switched['session_token']
        status,after=self.request('GET','/api/account/overview',target_token)
        self.assertEqual(status,200)
        self.assertEqual(after['tenant_id'],'cleaning')
        self.assertIsNone(after['social_connections'])
        status,_=self.request('POST','/api/account/logout',target_token,{})
        self.assertEqual(status,200)
        self.assertEqual(self.request('GET','/api/account/overview',target_token)[0],403)
        self.assertEqual(self.request('GET','/api/account/overview',self.token)[0],200)

    def test_create_held_draft_and_tenant_isolation(self):
        payload={'channel':'facebook','draft_text':'New product preview',
                 'suggestion':'Take a product photograph',
                 'required_items':['photo']}
        status,created=self.request('POST','/api/content/drafts',self.token,payload)
        self.assertEqual(status,200)
        self.assertEqual(created['status'],'needs_content')
        self.assertFalse(created['publishing_enabled'])
        _,first=self.request('GET','/api/account/overview',self.token)
        self.assertEqual(first['pending_content_requests'][0]['draft_text'],
                         'New product preview')
        _,switched=self.request('POST','/api/account/activate',self.token,
                                {'target_tenant_id':'cleaning'})
        _,second=self.request('GET','/api/account/overview',
                              switched['session_token'])
        self.assertEqual(second['pending_content_requests'],[])
        self.assertEqual(self.request('POST','/api/content/drafts',
                         switched['session_token'],payload)[0],200)
        _,first_again=self.request('GET','/api/account/overview',self.token)
        self.assertEqual(len(first_again['pending_content_requests']),1)

    def test_role_revocation_rejects_source_token(self):
        self.db.execute('UPDATE members SET role=? WHERE tenant_id=? AND subject_id=?',
                        (Role.VIEWER.value,'retail','owner'))
        self.db.commit()
        self.assertEqual(self.request('GET','/api/account/overview',self.token)[0],403)
        self.assertEqual(self.request('POST','/api/account/activate',self.token,
                         {'target_tenant_id':'cleaning'})[0],403)

if __name__=='__main__':unittest.main()
