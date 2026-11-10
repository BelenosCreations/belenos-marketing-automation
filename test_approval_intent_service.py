import hashlib
import sqlite3
import unittest
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from content_requests import ContentRequests
from content_attachments import AttachmentRegistry
from content_request_service import ContentRequestService
from truthguard_review_receipt import create_review_receipt
from approval_intent_service import ApprovalIntentService

class ApprovalIntentTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.directory=AccountDirectory(self.db)
        self.directory.bootstrap_owner('shop','owner')
        self.directory.bootstrap_owner('other','otherowner')
        self.sessions=SessionStore(self.db)
        self.owner=self.sessions.issue(Principal('owner','shop',Role.OWNER),now=100)
        self.other=self.sessions.issue(Principal('otherowner','other',Role.OWNER),now=100)
        self.requests=ContentRequests(self.db)
        self.service=ContentRequestService(requests=self.requests,
            sessions=self.sessions,directory=self.directory,
            attachments=AttachmentRegistry(self.db))
        self.id=self.requests.create(tenant_id='shop',channel='facebook',
            draft_text='A custom print',suggestion='Photo',required_items=['photo'],now=100)
        self.ledger=ApprovalIntentService(db=self.db,sessions=self.sessions,
            directory=self.directory,content_service=self.service)
        self.receipt=self.make_receipt()

    def make_receipt(self):
        draft=self.requests.get(tenant_id='shop',request_id=self.id)['draft_text']
        report={'business_id':'shop','request_id':self.id,'status':'held',
                'publishing_enabled':False,
                'span_audit':{'draft_sha256':hashlib.sha256(draft.encode()).hexdigest()}}
        return create_review_receipt(tenant_id='shop',request_id=self.id,
            draft_text=draft,review=report,reviewed_at=101)

    def complete(self):
        self.requests.provide(tenant_id='shop',request_id=self.id,item='photo',
            content_reference='verified-attachment:test',now=101)

    def record(self,**kwargs):
        args=dict(token=self.owner,tenant_id='shop',request_id=self.id,
                  receipt=self.receipt,now=102)
        args.update(kwargs)
        return self.ledger.record(**args)

    def test_incomplete_content_rejected(self):
        with self.assertRaises(ValueError):self.record()

    def test_owner_intent_is_not_publish_permission(self):
        self.complete()
        record=self.record()
        self.assertFalse(record['publishing_enabled'])
        self.assertTrue(self.ledger.inspect(token=self.owner,tenant_id='shop',
            intent_id=record['intent_id'],now=103)['active'])

    def test_other_business_denied(self):
        self.complete()
        with self.assertRaises(PermissionError):self.record(token=self.other)

    def test_stale_receipt_denied(self):
        self.complete()
        self.receipt['payload']['draft_sha256']='bad'
        with self.assertRaises(ValueError):self.record()

    def test_content_hold_requires_new_review(self):
        self.complete()
        record=self.record()
        self.requests.set_hold(tenant_id='shop',request_id=self.id,
                               status='postponed',now=103)
        result=self.ledger.inspect(token=self.owner,tenant_id='shop',
            intent_id=record['intent_id'],now=104)
        self.assertFalse(result['content_complete'])
        self.assertTrue(result['requires_new_review'])
        self.assertFalse(result['publishing_enabled'])

    def test_replacing_photo_requires_new_review(self):
        self.complete()
        record=self.record()
        self.requests.provide(tenant_id='shop',request_id=self.id,item='photo',
            content_reference='verified-attachment:replacement',now=103)
        result=self.ledger.inspect(token=self.owner,tenant_id='shop',
            intent_id=record['intent_id'],now=104)
        self.assertTrue(result['draft_unchanged'])
        self.assertTrue(result['content_complete'])
        self.assertFalse(result['content_unchanged'])
        self.assertTrue(result['requires_new_review'])

    def test_unchanged_content_remains_current(self):
        self.complete()
        record=self.record()
        result=self.ledger.inspect(token=self.owner,tenant_id='shop',
            intent_id=record['intent_id'],now=103)
        self.assertTrue(result['content_unchanged'])
        self.assertFalse(result['requires_new_review'])

    def test_legacy_record_without_content_digest_requires_review(self):
        self.complete()
        record=self.record()
        self.db.execute('UPDATE approval_intents SET content_sha256=NULL WHERE intent_id=?',
                        (record['intent_id'],))
        self.db.commit()
        result=self.ledger.inspect(token=self.owner,tenant_id='shop',
            intent_id=record['intent_id'],now=103)
        self.assertTrue(result['requires_new_review'])

    def test_revocation(self):
        self.complete()
        record=self.record()
        self.assertTrue(self.ledger.revoke(token=self.owner,tenant_id='shop',
            intent_id=record['intent_id'],now=103))
        self.assertFalse(self.ledger.inspect(token=self.owner,tenant_id='shop',
            intent_id=record['intent_id'],now=104)['active'])

if __name__=='__main__':unittest.main()
