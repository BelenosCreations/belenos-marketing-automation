import sqlite3
import unittest
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from content_requests import ContentRequests
from content_request_service import ContentRequestService

class ContentRequestServiceTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.directory=AccountDirectory(self.db)
        self.directory.bootstrap_owner('shop','owner')
        self.directory.bootstrap_owner('other','other_owner')
        for name,role in [('manager',Role.MARKETING_MANAGER),
                          ('creator',Role.CONTENT_CREATOR),
                          ('viewer',Role.VIEWER)]:
            self.directory.set_member(Principal('owner','shop',Role.OWNER),name,role)
        self.sessions=SessionStore(self.db)
        self.tokens={name:self.sessions.issue(Principal(name,'shop',role),now=100)
                     for name,role in [('owner',Role.OWNER),
                        ('manager',Role.MARKETING_MANAGER),
                        ('creator',Role.CONTENT_CREATOR),
                        ('viewer',Role.VIEWER)]}
        self.service=ContentRequestService(requests=ContentRequests(self.db),
            sessions=self.sessions,directory=self.directory)
        self.args=dict(tenant_id='shop',channel='facebook',draft_text='Custom work',
                       suggestion='Photograph finished product',
                       required_items=['photo','permission'],now=101)

    def create(self,user='owner',**kwargs):
        args=dict(self.args)
        args.update(kwargs)
        return self.service.create(token=self.tokens[user],**args)

    def test_owner_can_create(self):
        self.assertTrue(self.create())

    def test_creator_can_create(self):
        self.assertTrue(self.create('creator'))

    def test_manager_can_create(self):
        self.assertTrue(self.create('manager'))

    def test_viewer_cannot_create(self):
        with self.assertRaises(PermissionError):self.create('viewer')

    def test_viewer_can_read(self):
        rid=self.create()
        self.assertEqual(self.service.get(token=self.tokens['viewer'],
            tenant_id='shop',request_id=rid,now=101)['draft_text'],'Custom work')

    def test_viewer_cannot_supply(self):
        rid=self.create()
        with self.assertRaises(PermissionError):
            self.service.provide(token=self.tokens['viewer'],tenant_id='shop',
                request_id=rid,item='photo',content_reference='asset:1',now=101)

    def test_cross_tenant_rejected(self):
        with self.assertRaises(PermissionError):self.create(tenant_id='other')
        with self.assertRaises(PermissionError):
            self.service.list_for_business(token=self.tokens['owner'],
                tenant_id='other',now=101)

    def test_deactivated_creator_rejected(self):
        self.directory.set_member(Principal('owner','shop',Role.OWNER),
                                  'creator',Role.CONTENT_CREATOR,active=False)
        with self.assertRaises(PermissionError):self.create('creator')

    def test_role_downgrade_enforced(self):
        self.directory.set_member(Principal('owner','shop',Role.OWNER),
                                  'manager',Role.VIEWER)
        with self.assertRaises(PermissionError):self.create('manager')

    def test_revoked_session_rejected(self):
        self.sessions.revoke(self.tokens['owner'],now=100)
        with self.assertRaises(PermissionError):self.create()

    def test_expired_session_rejected(self):
        with self.assertRaises(PermissionError):self.create(now=4000)

    def test_unknown_token_rejected(self):
        with self.assertRaises(PermissionError):
            self.service.create(token='invalid',**self.args)

    def test_owner_can_complete_but_not_publish(self):
        rid=self.create()
        self.assertEqual(self.service.provide(token=self.tokens['owner'],
            tenant_id='shop',request_id=rid,item='photo',
            content_reference='asset:1',now=102),'needs_content')
        self.assertEqual(self.service.provide(token=self.tokens['owner'],
            tenant_id='shop',request_id=rid,item='permission',
            content_reference='permission:2',now=103),'ready_for_review')

    def test_owner_can_postpone(self):
        rid=self.create()
        self.assertEqual(self.service.set_hold(token=self.tokens['owner'],
            tenant_id='shop',request_id=rid,status='postponed',now=102),'postponed')

if __name__=='__main__':unittest.main()
