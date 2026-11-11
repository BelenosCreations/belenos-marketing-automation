"""Two independently initialized offline BAM clients share one durable DB.

This integration is a local *simulation* of separate app/device sessions.
It is NOT a multi-device hosted deployment, an invitation delivery system,
production DB load test, or permission to schedule/publish.
"""
import io
import json
import os
import sqlite3
import tempfile
import unittest

from access_policy import Principal, Role
from bam_offline_gateway import BAMOfflineGateway


class TwoClientCollaborationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='bam-multi-client-')
        self.path=os.path.join(self.temp.name,'bam.sqlite3')
        self.db1=sqlite3.connect(self.path,timeout=5)
        self.app1=BAMOfflineGateway(
            self.db1,enabled=True,clock=lambda:101)
        self.owner_id=self.app1.identities.register_password(
            email='owner@example.com',
            password='owner strong password phrase',now=100)
        self.editor_id=self.app1.identities.register_password(
            email='editor@example.com',
            password='editor strong password phrase',now=100)
        for identity in (self.owner_id,self.editor_id):
            self.app1.identities.set_email_verified_trusted(
                subject_id=identity,verified=True)
        self.app1.directory.bootstrap_owner('shop',self.owner_id)
        self.app1.directory.bootstrap_owner('other','other-owner')
        self.app1.directory.set_member(
            Principal(self.owner_id,'shop',Role.OWNER),
            self.editor_id,Role.CONTENT_CREATOR)
        self.app1.directory.set_member(
            Principal('other-owner','other',Role.OWNER),
            self.editor_id,Role.VIEWER)
        self.app1.curation.create_profile(
            'shop','Shared Shop','retail',['custom work'])
        self.app1.curation.create_profile(
            'other','Independent Firm','services',['facility care'])
        # Distinct connections and service objects: not a single mocked
        # in-memory context masquerading as two signed-in people.
        self.db2=sqlite3.connect(self.path,timeout=5)
        self.app2=BAMOfflineGateway(
            self.db2,enabled=True,clock=lambda:101)
        self.owner=self.login(self.app1,
            'owner@example.com','owner strong password phrase','shop')
        self.editor_shop=self.login(self.app2,
            'editor@example.com','editor strong password phrase','shop')
        self.editor_other=self.login(self.app2,
            'editor@example.com','editor strong password phrase','other')

    def tearDown(self):
        self.db2.close()
        self.db1.close()
        self.temp.cleanup()

    @staticmethod
    def call(app,path,*,method='GET',body=None,token=None):
        environ={'PATH_INFO':path,'REQUEST_METHOD':method,
                 'wsgi.url_scheme':'https'}
        if token is not None:
            environ['HTTP_AUTHORIZATION']='Bearer '+token
        if body is not None:
            raw=json.dumps(body).encode('utf-8')
            environ.update({'CONTENT_TYPE':'application/json',
                            'CONTENT_LENGTH':str(len(raw)),
                            'wsgi.input':io.BytesIO(raw)})
        result={}
        payload=b''.join(app(environ,lambda status,headers:
            result.update(status=status,headers=dict(headers))))
        return result,json.loads(payload)

    def login(self,app,email,password,tenant):
        meta,body=self.call(app,'/api/v1/auth/password',
            method='POST',body={'email':email,'password':password,
                                'tenant_id':tenant})
        self.assertEqual(meta['status'],'200 OK')
        self.assertFalse(body['publishing_enabled'])
        return body['session_token']

    def create_shared(self):
        meta,body=self.call(self.app1,'/api/v1/content/drafts',
            method='POST',token=self.owner,body={
                'channel':'facebook','draft_text':'Shared product announcement',
                'suggestion':'Add a cleared original photo',
                'required_items':['photo']})
        self.assertEqual(meta['status'],'201 Created')
        return body['request_id']

    def test_two_distinct_clients_share_drafts_with_stale_edit_conflicts(self):
        rid=self.create_shared()
        _,read=self.call(self.app2,'/api/v1/drafts',token=self.editor_shop)
        item=next(x for x in read['drafts'] if x['request_id']==rid)
        self.assertEqual(item['revision'],1)
        self.assertEqual(item['draft_text'],'Shared product announcement')

        _,other=self.call(self.app2,'/api/v1/drafts',token=self.editor_other)
        self.assertFalse(any(x['request_id']==rid for x in other['drafts']))
        # Both clients saw revision 1. First writer succeeds, other fails.
        meta,edited=self.call(self.app1,'/api/v1/content/drafts',
            method='PUT',token=self.owner,body={
                'request_id':rid,'target':'draft_text',
                'revised_text':'Verified draft wording',
                'expected_revision':1})
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(edited['revision'],2)
        meta,rejected=self.call(self.app2,'/api/v1/content/drafts',
            method='PUT',token=self.editor_shop,body={
                'request_id':rid,'target':'draft_text',
                'revised_text':'Stale overwrite','expected_revision':1})
        self.assertEqual(meta['status'],'409 Conflict')
        self.assertNotIn('draft_text',rejected)
        _,refreshed=self.call(self.app2,'/api/v1/drafts',
            token=self.editor_shop)
        self.assertEqual(next(x for x in refreshed['drafts']
            if x['request_id']==rid)['draft_text'],'Verified draft wording')
        # Client 2 can now edit a different component on the new revision.
        meta,revised=self.call(self.app2,'/api/v1/content/drafts',
            method='PUT',token=self.editor_shop,body={
                'request_id':rid,'target':'suggestion',
                'revised_text':'Photograph the finished project',
                'expected_revision':2})
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(revised['revision'],3)
        _,stored=self.call(self.app1,'/api/v1/drafts',token=self.owner)
        result=next(x for x in stored['drafts'] if x['request_id']==rid)
        self.assertEqual(result['draft_text'],'Verified draft wording')
        self.assertEqual(result['suggestion'],
                         'Photograph the finished project')
        self.assertFalse(stored['publishing_enabled'])
        self.assertEqual(self.call(self.app1,'/api/v1/publish')[0]['status'],
                         '404 Not Found')

    def test_team_change_revokes_one_business_not_other_and_survives_restart(self):
        rid=self.create_shared()
        meta,changed=self.call(self.app1,'/api/v1/team/membership',
            method='POST',token=self.owner,body={
                'member_id':self.editor_id,'action':'change_role',
                'role':'viewer','expected_revision':1})
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(changed['sessions_revoked'],1)
        self.assertEqual(self.call(self.app2,'/api/v1/drafts',
            token=self.editor_shop)[0]['status'],'401 Unauthorized')
        self.assertEqual(self.call(self.app2,'/api/v1/dashboard',
            token=self.editor_other)[0]['status'],'200 OK')
        self.assertEqual(self.call(self.app2,'/api/v1/team/activity',
            token=self.editor_other)[0]['status'],'401 Unauthorized')
        meta,audit=self.call(self.app1,'/api/v1/team/activity',
            token=self.owner)
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(len(audit['events']),1)
        self.assertEqual(audit['events'][0]['action'],'change_role')
        self.assertNotIn('editor@example.com',str(audit))
        # A newly initialized instance with the same durable SQLite file
        # sees the current team role, data and scoped session revocations.
        self.db2.close()
        self.db2=sqlite3.connect(self.path,timeout=5)
        self.app2=BAMOfflineGateway(
            self.db2,enabled=True,clock=lambda:102)
        self.assertEqual(self.call(self.app2,'/api/v1/dashboard',
            token=self.editor_other)[0]['status'],'200 OK')
        self.assertEqual(self.call(self.app2,'/api/v1/drafts',
            token=self.editor_shop)[0]['status'],'401 Unauthorized')
        replacement=self.login(self.app2,
            'editor@example.com','editor strong password phrase','shop')
        _,drafts=self.call(self.app2,'/api/v1/drafts',token=replacement)
        self.assertEqual(next(x for x in drafts['drafts']
            if x['request_id']==rid)['status'],'needs_content')
        meta,_=self.call(self.app2,'/api/v1/content/drafts',token=replacement,
            method='PUT',body={
                'request_id':rid,'target':'draft_text',
                'revised_text':'Viewer tried an edit','expected_revision':1})
        self.assertEqual(meta['status'],'401 Unauthorized')
        meta,team=self.call(self.app1,'/api/v1/team/members',
            token=self.owner)
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(next(x for x in team['members']
            if x['member_id']==self.editor_id)['role'],'viewer')


if __name__=='__main__':
    unittest.main()
