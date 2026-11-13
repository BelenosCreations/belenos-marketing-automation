"""Private image ingestion never changes attachment verification status."""
import hashlib
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from content_requests import ContentRequests
from content_attachments import AttachmentRegistry
from content_request_service import ContentRequestService
from content_upload_preflight import ContentUploadPreflight
from bam_pending_media_store import BAMPendingMediaStore

from synthetic_media_fixture import PNG

class PendingMediaStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=sqlite3.connect(':memory:')
        self.dir=AccountDirectory(self.db)
        self.dir.bootstrap_owner('shop','owner')
        self.dir.bootstrap_owner('other','otherowner')
        self.sessions=SessionStore(self.db)
        self.token=self.sessions.issue(Principal('owner','shop',Role.OWNER),now=100)
        self.other=self.sessions.issue(Principal('otherowner','other',Role.OWNER),now=100)
        self.attachments=AttachmentRegistry(self.db)
        self.requests=ContentRequests(self.db)
        self.service=ContentRequestService(requests=self.requests,
            sessions=self.sessions,directory=self.dir,attachments=self.attachments)
        self.rid=self.service.create(token=self.token,tenant_id='shop',
            channel='facebook',draft_text='Test artwork',
            suggestion='Supply an image',required_items=['image'],now=101)
        self.pending=ContentUploadPreflight(service=self.service).begin(
            token=self.token,tenant_id='shop',request_id=self.rid,item='image',
            media_type='image/png',sha256=hashlib.sha256(PNG).hexdigest(),
            byte_count=len(PNG),now=101)
        self.store=BAMPendingMediaStore(
            service=self.service,storage_dir=str(Path(self.tmp.name)/'pending'))
    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_receipt_is_private_pending_only_and_nonpublishable(self):
        attachment=self.pending['attachment_id']
        result=self.store.receive(token=self.token,attachment_id=attachment,
            content=PNG,now=102)
        self.assertEqual(result['status'],'pending_scan')
        self.assertEqual(result['bytes_received'],len(PNG))
        self.assertFalse(result['media_verified'])
        self.assertFalse(result['publishing_enabled'])
        self.assertIsNone(self.attachments.resolve_verified(
            tenant_id='shop',request_id=self.rid,item='image',
            attachment_id=attachment))
        self.assertEqual(self.requests.get(tenant_id='shop',
            request_id=self.rid)['status'],'needs_content')
        file=Path(self.tmp.name)/'pending'/(attachment+'.pending')
        self.assertEqual(file.read_bytes(),PNG)
        if os.name=='posix':
            self.assertEqual(file.stat().st_mode&0o077,0)
            self.assertEqual(file.parent.stat().st_mode&0o077,0)
        with self.assertRaises(FileExistsError):
            self.store.receive(token=self.token,attachment_id=attachment,
                content=PNG,now=103)


    def test_statuses_are_scoped_and_never_verify_media(self):
        before=self.store.statuses(token=self.token,now=102)
        self.assertEqual(before['items'],[{
            'request_id':self.rid,'item':'image','status':'awaiting_file'}])
        self.assertFalse(before['media_verified'])
        self.assertFalse(before['publishing_enabled'])
        self.assertEqual(self.store.statuses(token=self.other,now=102)['items'],[])
        self.store.receive(token=self.token,
            attachment_id=self.pending['attachment_id'],content=PNG,now=102)
        after=self.store.statuses(token=self.token,now=103)
        self.assertEqual(after['items'][0]['status'],'pending_scan')
        self.assertNotIn(self.pending['attachment_id'],str(after))
        self.assertNotIn(str(self.store.root),str(after))
        with self.assertRaises(PermissionError):
            self.store.statuses(token='invalid',now=103)
        self.service.set_hold(token=self.token,tenant_id='shop',
            request_id=self.rid,status='postponed',now=104)
        self.assertEqual(self.store.statuses(token=self.token,now=105)['items'],[])
        self.service.set_hold(token=self.token,tenant_id='shop',
            request_id=self.rid,status='needs_content',now=106)
        self.assertEqual(self.store.statuses(token=self.token,now=107)
                         ['items'][0]['status'],'pending_scan')

    def test_status_read_rejects_symlinked_receipt(self):
        target=self.store.root/(self.pending['attachment_id']+'.pending')
        try:
            target.symlink_to(Path(self.tmp.name)/'untrusted-target')
        except OSError:
            self.skipTest('Symlink unsupported')
        result=self.store.statuses(token=self.token,now=102)
        self.assertEqual(result['items'][0]['status'],'awaiting_file')


    def test_discard_removes_only_private_pending_content(self):
        attachment=self.pending['attachment_id']
        self.store.receive(token=self.token,attachment_id=attachment,
                           content=PNG,now=102)
        private=self.store.root/(attachment+'.pending')
        self.assertTrue(private.exists())
        with self.assertRaises((KeyError,PermissionError)):
            self.store.discard(token=self.other,request_id=self.rid,
                               item='image',now=103)
        self.assertTrue(private.exists())
        removed=self.store.discard(token=self.token,request_id=self.rid,
                                   item='image',now=103)
        self.assertEqual(removed['removed'],1)
        self.assertFalse(removed['media_verified'])
        self.assertFalse(removed['publishing_enabled'])
        self.assertFalse(private.exists())
        self.assertEqual(self.store.statuses(token=self.token,now=104)['items'],[])
        self.assertEqual(self.store.discard(token=self.token,
            request_id=self.rid,item='image',now=105)['removed'],0)
        self.assertEqual(self.requests.get(tenant_id='shop',
            request_id=self.rid)['status'],'needs_content')
        self.assertIsNone(self.attachments.resolve_verified(
            tenant_id='shop',request_id=self.rid,item='image',
            attachment_id=attachment))
        with self.assertRaises(ValueError):
            self.store.discard(token=self.token,request_id=self.rid,
                               item='not-required',now=106)

    def test_discard_unreceived_metadata_and_symlink_without_following(self):
        path=self.store.root/(self.pending['attachment_id']+'.pending')
        outside=Path(self.tmp.name)/'outside.txt'
        outside.write_bytes(b'Do not remove this external target')
        try:
            path.symlink_to(outside)
        except OSError:
            self.skipTest('Symlink unsupported')
        result=self.store.discard(token=self.token,request_id=self.rid,
                                  item='image',now=102)
        self.assertEqual(result['removed'],1)
        self.assertFalse(path.exists())
        self.assertEqual(outside.read_bytes(),b'Do not remove this external target')

    def test_wrong_user_digest_type_and_closed_request_rejected(self):
        attachment=self.pending['attachment_id']
        with self.assertRaises((PermissionError,KeyError)):
            self.store.receive(token=self.other,attachment_id=attachment,
                content=PNG,now=102)
        with self.assertRaises(ValueError):
            self.store.receive(token=self.token,attachment_id=attachment,
                content=b'evil',now=102)
        with self.assertRaises(ValueError):
            self.store.receive(token=self.token,attachment_id=attachment,
                content=b'\x89PNG\r\n\x1a\nwrong',now=102)
        with self.assertRaises(ValueError):
            self.store.receive(token=self.token,attachment_id=attachment,
                content=b'',now=102)
        self.service.set_hold(token=self.token,tenant_id='shop',
            request_id=self.rid,status='postponed',now=102)
        with self.assertRaises(PermissionError):
            self.store.receive(token=self.token,attachment_id=attachment,
                content=PNG,now=103)
        self.assertFalse(list((Path(self.tmp.name)/'pending').iterdir()))

    def test_storage_refuses_source_checkout_and_unsafe_permissions(self):
        with self.assertRaises(ValueError):
            BAMPendingMediaStore(service=self.service,
                storage_dir=str(Path(__file__).resolve().parent/'private-media'))
        folder=Path(self.tmp.name)/'public'
        folder.mkdir(mode=0o777)
        if os.name=='posix':
            folder.chmod(0o755)
            with self.assertRaises(PermissionError):
                BAMPendingMediaStore(service=self.service,
                    storage_dir=str(folder))
        self.assertFalse(folder.joinpath(self.pending['attachment_id']+'.pending').exists())

if __name__=='__main__':unittest.main()
