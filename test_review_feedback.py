"""Collaborative draft feedback is isolated and never an approval."""
import sqlite3
import unittest
from access_policy import Principal, Role
from accounts import AccountDirectory
from sessions import SessionStore
from content_requests import ContentRequests
from content_attachments import AttachmentRegistry
from content_request_service import ContentRequestService
from review_feedback import ReviewFeedback

class ReviewFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.directory=AccountDirectory(self.db)
        self.directory.bootstrap_owner('shop','owner')
        self.directory.bootstrap_owner('other','other')
        owner=Principal('owner','shop',Role.OWNER)
        self.directory.set_member(owner,'manager',Role.MARKETING_MANAGER)
        self.directory.set_member(owner,'creator',Role.CONTENT_CREATOR)
        self.directory.set_member(owner,'viewer',Role.VIEWER)
        self.sessions=SessionStore(self.db)
        self.owner=self.sessions.issue(owner,now=100)
        self.manager=self.sessions.issue(
            Principal('manager','shop',Role.MARKETING_MANAGER),now=100)
        self.creator=self.sessions.issue(
            Principal('creator','shop',Role.CONTENT_CREATOR),now=100)
        self.viewer=self.sessions.issue(
            Principal('viewer','shop',Role.VIEWER),now=100)
        self.other=self.sessions.issue(
            Principal('other','other',Role.OWNER),now=100)
        self.requests=ContentRequests(self.db)
        self.attachments=AttachmentRegistry(self.db)
        self.content=ContentRequestService(
            requests=self.requests,sessions=self.sessions,
            directory=self.directory,attachments=self.attachments)
        self.rid=self.content.create(token=self.owner,tenant_id='shop',
            channel='facebook',draft_text='Example marketing text',
            suggestion='Add photo',required_items=['image'],now=101)
        self.service=ReviewFeedback(
            db=self.db,sessions=self.sessions,directory=self.directory,
            content_service=self.content)

    def save(self, **kwargs):
        args=dict(token=self.owner,now=102,request_id=self.rid,
                  expected_revision=1,expected_feedback_token=None,
                  note='Please confirm product photo rights.')
        args.update(kwargs)
        return self.service.save(**args)

    def list(self,token=None):
        return self.service.list_current_business(
            token=token or self.owner,now=105)

    def test_creates_private_review_comment_without_approval(self):
        before=self.requests.get(tenant_id='shop',request_id=self.rid)
        result=self.save()
        self.assertFalse(result['approval_granted'])
        self.assertFalse(result['publishing_enabled'])
        row=self.list()['items'][0]
        self.assertFalse(row['stale'])
        self.assertEqual(row['draft_revision'],1)
        self.assertEqual(row['note'],'Please confirm product photo rights.')
        self.assertFalse(row['approval_granted'])
        self.assertEqual(self.requests.get(
            tenant_id='shop',request_id=self.rid),before)
        self.assertEqual(self.list(token=self.viewer)['items'][0]['note'],
                         row['note'])
        self.assertEqual(self.list(token=self.other)['items'],[])

    def test_stale_edit_delete_and_recreate_blocked(self):
        original=self.save()
        version=original['feedback_token']
        updated=self.save(token=self.manager,
            expected_feedback_token=version,note='Please check artwork')
        self.assertNotEqual(version,updated['feedback_token'])
        with self.assertRaises(ValueError):
            self.save(expected_feedback_token=version)
        with self.assertRaises(ValueError):
            self.service.discard(token=self.owner,now=102,
                request_id=self.rid,expected_feedback_token=version)
        self.assertEqual(self.service.discard(
            token=self.manager,now=103,request_id=self.rid,
            expected_feedback_token=updated['feedback_token'])['removed'],1)
        recreated=self.save()
        self.assertNotEqual(recreated['feedback_token'],version)
        with self.assertRaises(ValueError):
            self.service.discard(token=self.owner,now=104,
                request_id=self.rid,expected_feedback_token=version)

    def test_stale_draft_revision_visible_but_no_implicit_clear(self):
        self.save()
        self.content.revise(token=self.creator,tenant_id='shop',
            request_id=self.rid,target='draft_text',
            revised_text='Updated wording',expected_revision=1,now=103)
        row=self.list()['items'][0]
        self.assertTrue(row['stale'])
        self.assertEqual(row['current_revision'],2)
        with self.assertRaises(ValueError):
            self.save(note='New review',expected_revision=1,
                      expected_feedback_token=row['feedback_token'])
        updated=self.save(note='New review',expected_revision=2,
                          expected_feedback_token=row['feedback_token'])
        self.assertNotEqual(updated['feedback_token'],row['feedback_token'])
        self.assertFalse(self.list()['items'][0]['stale'])

    def test_creator_viewer_cannot_edit_or_remove(self):
        for token in (self.creator,self.viewer,self.other,'bogus'):
            with self.assertRaises(PermissionError):
                self.save(token=token)
        created=self.save()
        for token in (self.creator,self.viewer,self.other,'bogus'):
            with self.assertRaises(PermissionError):
                self.service.discard(token=token,now=103,
                    request_id=self.rid,
                    expected_feedback_token=created['feedback_token'])
        self.assertEqual(len(self.list()['items']),1)

    def test_reject_unsafe_payload_and_invalid_draft(self):
        for value in ('','   ',' padded ','x'*1001,'a\x00b',42):
            with self.assertRaises(ValueError):
                self.save(note=value)
        for version in ('bogus',True,17):
            with self.assertRaises(ValueError):
                self.save(expected_feedback_token=version)
        with self.assertRaises(ValueError):
            self.save(expected_revision=True)
        with self.assertRaises(KeyError):
            self.save(request_id='b'*32)
        with self.assertRaises(ValueError):
            self.save(now=True)
        self.assertEqual(self.list()['items'],[])

    def test_deactivated_role_invalidates_existing_session(self):
        self.directory.set_member(Principal('owner','shop',Role.OWNER),
                                  'manager',Role.VIEWER)
        with self.assertRaises(PermissionError):
            self.save(token=self.manager)
        with self.assertRaises(PermissionError):
            self.list(token=self.manager)

if __name__=='__main__':
    unittest.main()
