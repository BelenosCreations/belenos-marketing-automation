import hashlib
import unittest
from copy import deepcopy
from truthguard_review_receipt import create_review_receipt,validate_review_receipt

class ReviewReceiptTests(unittest.TestCase):
    def setUp(self):
        self.draft='Custom artwork $18'
        self.review={'business_id':'shop','request_id':'req1','status':'held',
                     'publishing_enabled':False,
                     'span_audit':{'draft_sha256':hashlib.sha256(
                         self.draft.encode('utf-8')).hexdigest()}}
        self.receipt=create_review_receipt(tenant_id='shop',request_id='req1',
            draft_text=self.draft,review=self.review,reviewed_at=123)

    def valid(self,**kwargs):
        args=dict(receipt=self.receipt,tenant_id='shop',
                  request_id='req1',draft_text=self.draft)
        args.update(kwargs)
        return validate_review_receipt(**args)

    def test_valid_receipt(self):
        self.assertTrue(self.valid())
        self.assertFalse(self.receipt['approval_granted'])

    def test_modified_draft_stale(self):
        self.assertFalse(self.valid(draft_text=self.draft+'!'))

    def test_cross_tenant_rejected(self):
        self.assertFalse(self.valid(tenant_id='other'))

    def test_wrong_request_rejected(self):
        self.assertFalse(self.valid(request_id='req2'))

    def test_tampered_review_rejected(self):
        altered=deepcopy(self.receipt)
        altered['payload']['review']['status']='verified'
        self.assertFalse(self.valid(receipt=altered))

    def test_claimed_approval_rejected(self):
        altered=deepcopy(self.receipt)
        altered['approval_granted']=True
        self.assertFalse(self.valid(receipt=altered))

    def test_wrong_fingerprint_rejected_on_create(self):
        with self.assertRaises(ValueError):
            create_review_receipt(tenant_id='shop',request_id='req1',
                draft_text='different',review=self.review,reviewed_at=123)

    def test_foreign_review_rejected_on_create(self):
        review=deepcopy(self.review)
        review['business_id']='other'
        with self.assertRaises(ValueError):
            create_review_receipt(tenant_id='shop',request_id='req1',
                draft_text=self.draft,review=review,reviewed_at=123)

if __name__=='__main__':unittest.main()
