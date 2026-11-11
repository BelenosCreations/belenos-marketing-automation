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
        for token in (self.creator,self.viewer,'bogus'):
            with self.assertRaises(PermissionError):
                self.save(token=token)
        with self.assertRaises(KeyError):
            self.save(token=self.other)
        created=self.save()
        for token in (self.creator,self.viewer,'bogus'):
            with self.assertRaises(PermissionError):
                self.service.discard(token=token,now=103,
                    request_id=self.rid,
                    expected_feedback_token=created['feedback_token'])
        with self.assertRaises(ValueError):
            self.service.discard(token=self.other,now=103,
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

    def test_history_is_private_metadata_not_deleted_with_note(self):
        created=self.save(now=102)
        updated=self.save(now=103,note='Use a consented photo',
                          expected_feedback_token=created['feedback_token'])
        self.service.discard(token=self.manager,now=104,
            request_id=self.rid,
            expected_feedback_token=updated['feedback_token'])
        history=self.service.history_current_business(
            token=self.owner,now=105)
        self.assertEqual(history['status'],'feedback_history_only')
        self.assertFalse(history['approval_granted'])
        self.assertFalse(history['publishing_enabled'])
        self.assertFalse(history['truncated'])
        self.assertEqual([event['action'] for event in history['events']],
                         ['removed','updated','created'])
        self.assertTrue(all(event['request_id']==self.rid
                            for event in history['events']))
        self.assertTrue(all(len(event['event_id'])==32
                            for event in history['events']))
        self.assertFalse(any('note' in event or 'actor_id' in event
                             for event in history['events']))
        self.assertEqual(self.list()['items'],[])
        self.assertEqual(self.service.history_current_business(
            token=self.other,now=105)['events'],[])
        for unprivileged in (self.creator,self.viewer,'invalid'):
            with self.assertRaises(PermissionError):
                self.service.history_current_business(
                    token=unprivileged,now=105)
        self.assertEqual(len(self.service.history_current_business(
            token=self.manager,now=105)['events']),3)

    def test_feedback_and_audit_write_share_transaction(self):
        self.db.execute("""CREATE TRIGGER reject_feedback_audit BEFORE
            INSERT ON bam_review_feedback_events
            BEGIN SELECT RAISE(ABORT,'audit unavailable'); END""")
        with self.assertRaises(ValueError):
            self.save()
        self.assertEqual(self.list()['items'],[])
        self.assertEqual(self.service.history_current_business(
            token=self.owner,now=105)['events'],[])
        self.db.execute('DROP TRIGGER reject_feedback_audit')
        created=self.save()
        self.db.execute("""CREATE TRIGGER reject_feedback_audit BEFORE
            INSERT ON bam_review_feedback_events
            BEGIN SELECT RAISE(ABORT,'audit unavailable'); END""")
        with self.assertRaises(sqlite3.IntegrityError):
            self.service.discard(token=self.owner,now=103,
                request_id=self.rid,
                expected_feedback_token=created['feedback_token'])
        self.assertEqual(len(self.list()['items']),1)
        self.assertEqual(len(self.service.history_current_business(
            token=self.owner,now=105)['events']),1)
        self.db.execute('DROP TRIGGER reject_feedback_audit')

    def test_history_caps_output_and_requires_current_membership(self):
        last=None
        for index in range(55):
            item=self.save(now=200+index,
                note='Review note '+str(index),
                expected_feedback_token=last)
            last=item['feedback_token']
        audit=self.service.history_current_business(
            token=self.owner,now=300)
        self.assertEqual(len(audit['events']),50)
        self.assertTrue(audit['truncated'])
        self.assertEqual(audit['events'][0]['occurred_at'],254)
        self.assertEqual(audit['events'][-1]['occurred_at'],205)
        self.directory.set_member(Principal('owner','shop',Role.OWNER),
                                  'manager',Role.VIEWER)
        with self.assertRaises(PermissionError):
            self.service.history_current_business(
                token=self.manager,now=300)

    def test_deactivated_role_invalidates_existing_session(self):
        self.directory.set_member(Principal('owner','shop',Role.OWNER),
                                  'manager',Role.VIEWER)
        with self.assertRaises(PermissionError):
            self.save(token=self.manager)
        with self.assertRaises(PermissionError):
            self.list(token=self.manager)

if __name__=='__main__':
    unittest.main()
