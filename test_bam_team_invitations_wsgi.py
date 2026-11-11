import io
import json
import unittest
from bam_team_invitations_wsgi import BAMTeamInvitationsWSGI

class Stub:
    def __init__(self):
        self.calls=[]
        self.denied=False
        self.extra=False
        self.history_extra=False
    def pending_current(self,**kwargs):
        self.calls.append(('list',kwargs))
        if self.denied: raise PermissionError('Not owner')
        result={'tenant_id':'shop','status':'private_pending_invitations',
            'items':[{'invitation_id':'a'*32,'email':'guest@example.com',
                      'role':'viewer','expires_at':7000}],
            'publishing_enabled':False}
        if self.extra: result['token_hash']='secret'
        return result
    def history_current(self,**kwargs):
        self.calls.append(('history',kwargs))
        if self.denied: raise PermissionError('Not owner')
        item={'invitation_id':'a'*32,
              'action':'cancelled','occurred_at':99}
        if self.history_extra:item['token_hash']='secret'
        return {'tenant_id':'shop','status':'private_invitation_activity',
                'events':[item],'publishing_enabled':False}

    def cancel_current(self,**kwargs):
        self.calls.append(('cancel',kwargs))
        if self.denied: raise PermissionError('Not owner')
        return {'tenant_id':'shop','invitation_id':kwargs['invitation_id'],
                'status':'cancelled','publishing_enabled':False}

class InviteWSGITests(unittest.TestCase):
    def setUp(self):
        self.svc=Stub()
        self.app=BAMTeamInvitationsWSGI(self.svc,enabled=True,clock=lambda:101)
    def call(self,*,path='/api/v1/team/invitations',method='GET',
             body=None,raw=None,app=None,**changes):
        env={'wsgi.url_scheme':'https','PATH_INFO':path,'REQUEST_METHOD':method,
             'HTTP_AUTHORIZATION':'Bearer '+'a'*43}
        if body is not None and raw is None: raw=json.dumps(body).encode()
        if raw is not None:
            env.update({'CONTENT_TYPE':'application/json',
                'CONTENT_LENGTH':str(len(raw)),'wsgi.input':io.BytesIO(raw)})
        env.update(changes)
        meta={}
        data=b''.join((app or self.app)(env,lambda status,headers:
            meta.update(status=status,headers=dict(headers))))
        return meta,json.loads(data)

    def test_private_list_and_cancel(self):
        meta,data=self.call()
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(meta['headers']['Cache-Control'],'no-store, private')
        self.assertEqual(data['items'][0]['role'],'viewer')
        self.assertNotIn('token_hash',str(data))
        self.assertEqual(self.svc.calls[0],
                         ('list',{'owner_session':'a'*43,'now':101}))
        meta,done=self.call(path='/api/v1/team/invitations/cancel',
            method='POST',body={'invitation_id':'a'*32})
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(done['status'],'cancelled')

    def test_owner_only_private_audit_metadata_and_strict_shape(self):
        meta,body=self.call(path='/api/v1/team/invitations/activity')
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(meta['headers']['Cache-Control'],'no-store, private')
        self.assertEqual(body['events'][0]['action'],'cancelled')
        self.assertEqual(body['events'][0]['invitation_id'],'a'*32)
        self.assertNotIn('token',str(body))
        self.assertNotIn('email',str(body))
        self.assertEqual(self.svc.calls[-1],
                         ('history',{'owner_session':'a'*43,'now':101}))
        self.svc.history_extra=True
        self.assertEqual(self.call(path='/api/v1/team/invitations/activity')
                         [0]['status'],'503 Service Unavailable')
        self.svc.history_extra=False
        self.svc.denied=True
        self.assertEqual(self.call(path='/api/v1/team/invitations/activity')
                         [0]['status'],'401 Unauthorized')
        self.svc.denied=False
        self.assertEqual(self.call(path='/api/v1/team/invitations/activity',
                                  method='POST',body={})[0]['status'],
                         '405 Method Not Allowed')
        self.assertEqual(self.call(path='/api/v1/team/invitations/activity',
                                  QUERY_STRING='tenant_id=other')[0]['status'],
                         '400 Bad Request')

    def test_no_new_invite_or_owner_grant(self):
        for bad in (
            {'invitation_id':'a'*32,'tenant_id':'other'},
            {'invitation_id':'a'*32,'role':'owner'},
            {'invitation_id':'not-an-id'},
            {'token':'a'*43},
        ):
            meta,_=self.call(path='/api/v1/team/invitations/cancel',
                method='POST',body=bad)
            self.assertEqual(meta['status'],'400 Bad Request')
        self.assertEqual(self.call(path='/api/v1/team/invitations/create',
            method='POST')[0]['status'],'404 Not Found')
        self.assertEqual(self.call(path='/api/v1/team/invitations',
            method='POST')[0]['status'],'405 Method Not Allowed')
        self.assertEqual(self.call(path='/api/v1/team/invitations/cancel',
            method='GET')[0]['status'],'405 Method Not Allowed')

    def test_auth_validation_and_forged_data(self):
        for opts,status in (
            ({'wsgi.url_scheme':'http',
              'HTTP_X_FORWARDED_PROTO':'https'},'403 Forbidden'),
            ({'HTTP_AUTHORIZATION':'Bearer bad'},'401 Unauthorized'),
            ({'QUERY_STRING':'tenant_id=other'},'400 Bad Request')):
            self.assertEqual(self.call(**opts)[0]['status'],status)
        self.svc.denied=True
        self.assertEqual(self.call()[0]['status'],'401 Unauthorized')
        self.svc.denied=False
        self.svc.extra=True
        self.assertEqual(self.call()[0]['status'],'503 Service Unavailable')

    def test_disabled_by_default(self):
        self.assertEqual(self.call(app=BAMTeamInvitationsWSGI())[0]['status'],
                         '503 Service Unavailable')
        with self.assertRaises(ValueError):
            BAMTeamInvitationsWSGI(self.svc,enabled=1)

if __name__=='__main__':
    unittest.main()
