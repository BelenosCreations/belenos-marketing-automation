import sqlite3
import unittest
from accounts import AccountDirectory
from sessions import SessionStore
from access_policy import Principal,Role
from content_requests import ContentRequests
from content_attachments import AttachmentRegistry
from content_request_service import ContentRequestService
from content_request_dashboard import ContentRequestDashboard

class DashboardTests(unittest.TestCase):
    def setUp(self):
        db=sqlite3.connect(':memory:')
        directory=AccountDirectory(db)
        directory.bootstrap_owner('shop','owner')
        directory.bootstrap_owner('other','otherowner')
        sessions=SessionStore(db)
        self.owner=sessions.issue(Principal('owner','shop',Role.OWNER),now=100)
        self.other=sessions.issue(Principal('otherowner','other',Role.OWNER),now=100)
        self.requests=ContentRequests(db)
        self.attachments=AttachmentRegistry(db)
        service=ContentRequestService(requests=self.requests,
            sessions=sessions,directory=directory,attachments=self.attachments)
        self.service=service
        self.dashboard=ContentRequestDashboard(service)
        self.rid=service.create(token=self.owner,tenant_id='shop',channel='facebook',
            draft_text='A recent custom project',suggestion='Capture a clear product photo',
            required_items=['photo','permission'],priority=4,now=101)

    def test_missing_items_visible(self):
        data=self.dashboard.overview(token=self.owner,tenant_id='shop',now=102)
        self.assertEqual(data['counts']['needs_content'],1)
        self.assertEqual(data['cards'][0]['missing_items'],['photo','permission'])
        self.assertFalse(data['cards'][0]['can_publish'])

    def test_completed_item_removed_from_missing(self):
        aid=self.attachments.register_pending(tenant_id='shop',request_id=self.rid,
            item='photo',media_type='image/png',sha256='a'*64,
            storage_key='private/one',now=102)
        self.attachments.validate_trusted(tenant_id='shop',attachment_id=aid,approved=True)
        self.service.provide(token=self.owner,tenant_id='shop',request_id=self.rid,
            item='photo',attachment_id=aid,now=103)
        data=self.dashboard.overview(token=self.owner,tenant_id='shop',now=104)
        self.assertEqual(data['cards'][0]['missing_items'],['permission'])
        self.assertEqual(data['counts']['needs_content'],1)

    def test_cross_business_dashboard_isolated(self):
        with self.assertRaises(PermissionError):
            self.dashboard.overview(token=self.owner,tenant_id='other',now=102)
        self.assertEqual(self.dashboard.overview(token=self.other,
            tenant_id='other',now=102)['cards'],[])

    def test_revoked_session_denied(self):
        self.service.sessions.revoke(self.owner,now=102)
        with self.assertRaises(PermissionError):
            self.dashboard.overview(token=self.owner,tenant_id='shop',now=103)

    def test_postponed_not_publishable(self):
        self.service.set_hold(token=self.owner,tenant_id='shop',
            request_id=self.rid,status='postponed',now=102)
        data=self.dashboard.overview(token=self.owner,tenant_id='shop',now=103)
        self.assertEqual(data['counts']['postponed'],1)
        self.assertFalse(data['cards'][0]['can_schedule'])

if __name__=='__main__':unittest.main()
