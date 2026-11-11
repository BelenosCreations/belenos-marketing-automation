"""No review-readiness preview can grant publishing or cross-tenant access."""
import sqlite3
import unittest
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from content_requests import ContentRequests
from content_attachments import AttachmentRegistry
from content_request_service import ContentRequestService
from review_readiness import ReviewReadiness

class ReviewReadinessTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.directory=AccountDirectory(self.db)
        self.directory.bootstrap_owner('shop','owner')
        self.directory.bootstrap_owner('other','another')
        self.directory.set_member(Principal('owner','shop',Role.OWNER),
                                  'viewer',Role.VIEWER)
        self.sessions=SessionStore(self.db)
        self.owner=self.sessions.issue(
            Principal('owner','shop',Role.OWNER),now=100)
        self.viewer=self.sessions.issue(
            Principal('viewer','shop',Role.VIEWER),now=100)
        self.other=self.sessions.issue(
            Principal('another','other',Role.OWNER),now=100)
        self.requests=ContentRequests(self.db)
        self.attachments=AttachmentRegistry(self.db)
        self.content=ContentRequestService(
            requests=self.requests,sessions=self.sessions,
            directory=self.directory,attachments=self.attachments)
        self.review=ReviewReadiness(
            sessions=self.sessions,directory=self.directory,
            content_service=self.content)
        self.rid=self.content.create(token=self.owner,tenant_id='shop',
            channel='facebook',draft_text='Example print',
            suggestion='Needs photo',required_items=['image'],now=101)

    def peek(self,token=None):
        return self.review.list_current_business(
            token=token or self.owner,now=102)

    def test_missing_content_is_held_and_read_only(self):
        before=self.requests.get(tenant_id='shop',request_id=self.rid)
        response=self.peek()
        self.assertEqual(response['status'],'review_preview_only')
        self.assertEqual(response['held_count'],1)
        self.assertEqual(response['editorial_material_complete_count'],0)
        item=response['items'][0]
        self.assertEqual(item['missing_items'],['image'])
        self.assertIn('truthguard_review_required',item['blockers'])
        self.assertFalse(item['approved'])
        self.assertFalse(response['publishing_enabled'])
        self.assertEqual(self.requests.get(
            tenant_id='shop',request_id=self.rid),before)

    def test_verified_media_is_editorially_complete_not_approved(self):
        aid=self.attachments.register_pending(tenant_id='shop',
            request_id=self.rid,item='image',media_type='image/png',
            sha256='a'*64,storage_key='private/shop/asset',
            now=101)
        self.attachments.validate_trusted(
            tenant_id='shop',attachment_id=aid,approved=True)
        self.content.provide(token=self.owner,tenant_id='shop',
            request_id=self.rid,item='image',attachment_id=aid,now=102)
        response=self.peek()
        self.assertEqual(response['editorial_material_complete_count'],1)
        item=response['items'][0]
        self.assertTrue(item['editorial_material_complete'])
        self.assertEqual(item['missing_items'],[])
        self.assertEqual(item['unverified_items'],[])
        self.assertIn('owner_approval_not_implemented',item['blockers'])
        self.assertIn('social_publishing_disabled',item['blockers'])
        self.assertFalse(item['approved'])

    def test_revoked_or_cross_request_media_not_complete(self):
        self.requests.provide(tenant_id='shop',request_id=self.rid,
            item='image',content_reference='verified-attachment:wrong',now=102)
        result=self.peek()['items'][0]
        self.assertFalse(result['editorial_material_complete'])
        self.assertEqual(result['unverified_items'],['image'])
        self.assertIn('unverified_or_unexpected_content',result['blockers'])

    def test_role_and_business_isolation(self):
        self.assertEqual(self.peek(token=self.viewer)['held_count'],1)
        self.assertEqual(self.peek(token=self.other)['held_count'],0)
        with self.assertRaises(PermissionError):
            self.review.list_current_business(token='invalid',now=102)
        with self.assertRaises(ValueError):
            self.review.list_current_business(token=self.owner,now=True)
        self.directory.set_member(Principal('owner','shop',Role.OWNER),
                                  'viewer',Role.CONTENT_CREATOR)
        with self.assertRaises(PermissionError):
            self.peek(token=self.viewer)

    def test_hold_state_is_not_complete(self):
        self.requests.set_hold(tenant_id='shop',request_id=self.rid,
                               status='postponed',now=102)
        row=self.peek()['items'][0]
        self.assertIn('draft_held',row['blockers'])
        self.assertFalse(row['editorial_material_complete'])

if __name__=='__main__':
    unittest.main()
