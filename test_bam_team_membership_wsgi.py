"""Strict owner-only WSGI team transport tests."""
import io
import json
import unittest

from bam_team_membership_wsgi import BAMTeamMembershipWSGI


class StubTeam:
    def __init__(self):
        self.calls=[]
        self.denied=False
        self.stale=False

    def list_current(self,**kwargs):
        self.calls.append(('list',kwargs))
        if self.denied:
            raise PermissionError('No access')
        return {'tenant_id':'shop','status':'private_team_preview',
                'members':[
                    {'member_id':'owner','role':'owner','active':True,
                     'revision':1,'email':'boss@example.com','is_self':True},
                    {'member_id':'person1','role':'viewer','active':True,
                     'revision':2,'email':'editor@example.com','is_self':False}],
                'publishing_enabled':False}

    def activity_current(self,**kwargs):
        self.calls.append(('activity',kwargs))
        if self.denied:
            raise PermissionError('Owner required')
        return {'tenant_id':'shop','status':'private_team_activity',
                'events':[{
                    'event_id':11,'member_id':'person1','actor_id':'owner',
                    'previous_role':'content_creator',
                    'resulting_role':'viewer','action':'change_role',
                    'changed_at':101,'revision_after':2}],
                'publishing_enabled':False}

    def change_current(self,**kwargs):
        self.calls.append(('change',kwargs))
        if self.denied:
            raise PermissionError('Not an owner')
        if self.stale:
            raise ValueError('Stale team membership revision')
        return {'tenant_id':'shop','member_id':kwargs['member_id'],
                'status':'updated' if kwargs['action']=='change_role'
                         else 'deactivated',
                'revision':kwargs['expected_revision']+1,
                'sessions_revoked':1,'publishing_enabled':False}


class TeamWSGITests(unittest.TestCase):
    def setUp(self):
        self.svc=StubTeam()
        self.app=BAMTeamMembershipWSGI(
            self.svc,enabled=True,clock=lambda:101)

    def call(self,*,path='/api/v1/team/members',method='GET',body=None,
             raw=None,app=None,**other):
        e={'wsgi.url_scheme':'https','PATH_INFO':path,
           'REQUEST_METHOD':method,
           'HTTP_AUTHORIZATION':'Bearer '+'a'*43}
        if raw is None and body is not None:
            raw=json.dumps(body).encode()
        if raw is not None:
            e.update({'CONTENT_TYPE':'application/json',
                      'CONTENT_LENGTH':str(len(raw)),
                      'wsgi.input':io.BytesIO(raw)})
        e.update(other)
        result={}
        payload=b''.join((app or self.app)(
            e,lambda status,headers:result.update(
                status=status,headers=dict(headers))))
        return result,json.loads(payload)

    def test_owner_list_stays_private(self):
        meta,data=self.call()
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(meta['headers']['Cache-Control'],'no-store, private')
        self.assertEqual(data['tenant_id'],'shop')
        self.assertEqual(len(data['members']),2)
        self.assertFalse(data['publishing_enabled'])
        self.assertEqual(self.svc.calls[0],
                         ('list',{'token':'a'*43,'now':101}))

    def test_private_team_activity_read_and_denial(self):
        meta,data=self.call(path='/api/v1/team/activity')
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(meta['headers']['Cache-Control'],'no-store, private')
        self.assertEqual(data['events'][0]['member_id'],'person1')
        self.assertNotIn('email',str(data))
        self.svc.denied=True
        self.assertEqual(self.call(path='/api/v1/team/activity')
                         [0]['status'],'401 Unauthorized')
        self.assertEqual(self.call(path='/api/v1/team/activity',
                         method='POST')[0]['status'],'405 Method Not Allowed')
        self.assertEqual(self.call(path='/api/v1/team/activity',
                         QUERY_STRING='tenant_id=other')[0]['status'],
                         '400 Bad Request')

    def test_revisioned_role_edit_and_deactivate(self):
        for action,body in [
            ('change_role',{'member_id':'person1','action':'change_role',
                            'role':'content_creator','expected_revision':2}),
            ('deactivate',{'member_id':'person1','action':'deactivate',
                           'expected_revision':2})]:
            meta,data=self.call(path='/api/v1/team/membership',
                method='POST',body=body)
            self.assertEqual(meta['status'],'200 OK')
            self.assertEqual(data['revision'],3)
            self.assertEqual(data['status'],
                             'updated' if action=='change_role' else 'deactivated')
            self.assertNotIn('role',data)

    def test_default_disabled_and_methods(self):
        self.assertEqual(self.call(app=BAMTeamMembershipWSGI())[0]['status'],
                         '503 Service Unavailable')
        self.assertEqual(self.call(path='/api/v1/team/membership')[0]['status'],
                         '405 Method Not Allowed')
        self.assertEqual(self.call(method='POST')[0]['status'],
                         '405 Method Not Allowed')
        self.assertEqual(self.call(path='/api/v1/publish')[0]['status'],
                         '404 Not Found')
        self.assertEqual(self.svc.calls,[])

    def test_strict_auth_and_https(self):
        for fields,status in [
            ({'wsgi.url_scheme':'http','HTTP_X_FORWARDED_PROTO':'https'},
             '403 Forbidden'),
            ({'HTTP_AUTHORIZATION':'Bearer wrong'},'401 Unauthorized'),
            ({'HTTP_AUTHORIZATION':'Bearer '+'a'*43+' '},'401 Unauthorized'),
            ({'QUERY_STRING':'tenant_id=other'},'400 Bad Request')]:
            self.assertEqual(self.call(**fields)[0]['status'],status)
        self.assertEqual(self.svc.calls,[])

    def test_no_tenant_override_or_owner_grant(self):
        base={'member_id':'person1','action':'change_role',
              'role':'viewer','expected_revision':1}
        for body in [
            {**base,'tenant_id':'other'},
            {**base,'role':'owner'},
            {**base,'expected_revision':True},
            {**base,'expected_revision':0},
            {'member_id':'person1','action':'deactivate',
             'expected_revision':1,'role':'viewer'},
            {'member_id':'person1','action':'deactivate'},
            {**base,'publishing_enabled':True},
            {**base,'member_id':'invalid id'}
        ]:
            with self.subTest(body=body):
                self.assertEqual(
                    self.call(path='/api/v1/team/membership',
                              method='POST',body=body)[0]['status'],
                    '400 Bad Request')
        self.assertEqual(self.svc.calls,[])

    def test_duplicate_json_and_truncated_body(self):
        for raw in (b'{"action":"deactivate","action":"change_role"}',
                    b'{',b'null',b'[]',b''):
            with self.subTest(raw=raw):
                self.assertEqual(self.call(
                    path='/api/v1/team/membership',method='POST',raw=raw)
                    [0]['status'],'400 Bad Request')
        self.assertEqual(self.svc.calls,[])

    def test_stale_and_unauthorized_does_not_expose_private_member(self):
        self.svc.stale=True
        meta,data=self.call(path='/api/v1/team/membership',
            method='POST',body={'member_id':'person1','action':'deactivate',
                                'expected_revision':1})
        self.assertEqual(meta['status'],'409 Conflict')
        self.assertNotIn('member_id',data)
        self.svc.denied=True
        self.assertEqual(self.call()[0]['status'],'401 Unauthorized')

    def test_untrusted_backend_response_fails_closed(self):
        original=self.svc.list_current
        self.svc.list_current=lambda **kwargs:{
            **original(**kwargs),'publishing_enabled':True}
        self.assertEqual(self.call()[0]['status'],'503 Service Unavailable')

    def test_invalid_enable_flag(self):
        with self.assertRaises(ValueError):
            BAMTeamMembershipWSGI(self.svc,enabled=1)


if __name__=='__main__':
    unittest.main()
