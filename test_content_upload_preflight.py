import sqlite3
import unittest
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from content_requests import ContentRequests
from content_attachments import AttachmentRegistry
from content_request_service import ContentRequestService
from content_upload_preflight import ContentUploadPreflight

class UploadPreflightTests(unittest.TestCase):
    def setUp(self):
        db=sqlite3.connect(':memory:')
        directory=AccountDirectory(db)
        directory.bootstrap_owner('shop','owner')
        directory.bootstrap_owner('other','otherowner')
        sessions=SessionStore(db)
        self.token=sessions.issue(Principal('owner','shop',Role.OWNER),now=100)
        self.other=sessions.issue(Principal('otherowner','other',Role.OWNER),now=100)
        attachments=AttachmentRegistry(db)
        self.service=ContentRequestService(requests=ContentRequests(db),
            sessions=sessions,directory=directory,attachments=attachments)
        self.preflight=ContentUploadPreflight(service=self.service)
        self.rid=self.service.create(token=self.token,tenant_id='shop',
            channel='facebook',draft_text='Example',suggestion='Take a photo',
            required_items=['photo'],now=101)
        self.args=dict(token=self.token,tenant_id='shop',request_id=self.rid,
            item='photo',media_type='image/png',sha256='a'*64,byte_count=1000,now=102)

    def test_preflight_is_pending_and_has_no_upload_url(self):
        result=self.preflight.begin(**self.args)
        self.assertEqual(result['status'],'pending')
        self.assertIsNone(result['upload_url'])
        self.assertIsNone(self.service.attachments.resolve_verified(
            tenant_id='shop',request_id=self.rid,item='photo',
            attachment_id=result['attachment_id']))

    def test_cross_business_denied(self):
        with self.assertRaises(PermissionError):
            self.preflight.begin(**dict(self.args,tenant_id='other'))

    def test_wrong_request_denied(self):
        with self.assertRaises(KeyError):
            self.preflight.begin(**dict(self.args,request_id='missing'))

    def test_wrong_checklist_item_denied(self):
        with self.assertRaises(ValueError):
            self.preflight.begin(**dict(self.args,item='not-requested'))

    def test_oversized_file_denied(self):
        with self.assertRaises(ValueError):
            self.preflight.begin(**dict(self.args,byte_count=21*1024*1024))

    def test_zero_file_denied(self):
        with self.assertRaises(ValueError):
            self.preflight.begin(**dict(self.args,byte_count=0))

    def test_unsupported_type_denied(self):
        with self.assertRaises(ValueError):
            self.preflight.begin(**dict(self.args,media_type='application/zip'))

    def test_postponed_request_denied(self):
        self.service.set_hold(token=self.token,tenant_id='shop',
            request_id=self.rid,status='postponed',now=102)
        with self.assertRaises(ValueError):
            self.preflight.begin(**self.args)

    def test_revoked_session_denied(self):
        self.service.sessions.revoke(self.token,now=101)
        with self.assertRaises(PermissionError):
            self.preflight.begin(**self.args)

    def test_server_generates_distinct_attachment_ids(self):
        a=self.preflight.begin(**self.args)
        b=self.preflight.begin(**self.args)
        self.assertNotEqual(a['attachment_id'],b['attachment_id'])

if __name__=='__main__':unittest.main()
