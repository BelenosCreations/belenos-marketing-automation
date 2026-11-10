import http.client
import json
import threading
import unittest
from dev_http_gateway import create_loopback_server

class FakeAPI:
    def get_overview(self,*,session_token,server_now):
        if session_token!='valid':
            raise PermissionError('denied')
        return {'tenant_id':'a','role':'owner','publishing_enabled':False}
    def activate_business(self,*,session_token,target_tenant_id,server_now):
        if session_token!='valid' or target_tenant_id!='b':
            raise PermissionError('denied')
        return {'session_token':'new-session','overview':{'tenant_id':'b'},
                'publishing_enabled':False}
    def logout(self,*,session_token,server_now):
        if session_token!='valid':
            raise PermissionError('denied')
        return {'signed_out':True,'publishing_enabled':False}

class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.server=create_loopback_server(FakeAPI(),clock=lambda:101)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
    def request(self,method,path,token='valid',body=None,content_type='application/json'):
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        headers={'Authorization':'Bearer '+token,'Content-Type':content_type}
        raw=json.dumps(body).encode() if body is not None else None
        conn.request(method,path,body=raw,headers=headers)
        response=conn.getresponse()
        result=response.status,dict(response.getheaders()),json.loads(response.read())
        conn.close()
        return result
    def test_overview(self):
        status,headers,body=self.request('GET','/api/account/overview')
        self.assertEqual(status,200)
        self.assertEqual(body['tenant_id'],'a')
        self.assertEqual(headers['Cache-Control'],'no-store')
    def test_activate(self):
        status,_,body=self.request('POST','/api/account/activate',body={'target_tenant_id':'b'})
        self.assertEqual(status,200)
        self.assertEqual(body['overview']['tenant_id'],'b')
    def test_logout(self):
        status,_,body=self.request('POST','/api/account/logout',body={})
        self.assertEqual(status,200)
        self.assertTrue(body['signed_out'])
    def test_bad_token_denied(self):
        self.assertEqual(self.request('GET','/api/account/overview',token='bad')[0],403)
    def test_extra_fields_denied(self):
        self.assertEqual(self.request('POST','/api/account/activate',
            body={'target_tenant_id':'b','role':'owner'})[0],400)
    def test_unknown_route(self):
        self.assertEqual(self.request('GET','/api/account/overview?token=valid')[0],404)
    def test_reject_public_bind(self):
        with self.assertRaises(ValueError):
            create_loopback_server(FakeAPI(),host='0.0.0.0')
    def test_browser_origin_denied(self):
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        conn.request('GET','/api/account/overview',
                     headers={'Authorization':'Bearer valid',
                              'Origin':'https://untrusted.example'})
        response=conn.getresponse()
        self.assertEqual(response.status,403)
        response.read()
        conn.close()

    def test_dns_rebinding_host_denied(self):
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        conn.request('GET','/api/account/overview',
                     headers={'Authorization':'Bearer valid',
                              'Host':'attacker.example'})
        response=conn.getresponse()
        self.assertEqual(response.status,403)
        response.read()
        conn.close()

    def test_content_type_required(self):
        self.assertEqual(self.request('POST','/api/account/logout',
            body={},content_type='text/plain')[0],400)

if __name__=='__main__':unittest.main()
