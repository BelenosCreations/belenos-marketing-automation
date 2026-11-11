import sqlite3
import unittest
from content_attachments import AttachmentRegistry

class AttachmentRegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry=AttachmentRegistry(sqlite3.connect(':memory:'))
        self.args=dict(tenant_id='shop',request_id='request1',item='photo',
            media_type='image/png',sha256='a'*64,storage_key='private/photo',now=100)

    def test_pending_cannot_complete(self):
        aid=self.registry.register_pending(**self.args)
        self.assertIsNone(self.registry.resolve_verified(tenant_id='shop',
            request_id='request1',item='photo',attachment_id=aid))

    def test_trusted_verification_enables_reference(self):
        aid=self.registry.register_pending(**self.args)
        self.registry.validate_trusted(tenant_id='shop',attachment_id=aid,approved=True)
        self.assertEqual(self.registry.resolve_verified(tenant_id='shop',
            request_id='request1',item='photo',attachment_id=aid),aid)

    def test_rejection_blocks_reference(self):
        aid=self.registry.register_pending(**self.args)
        self.registry.validate_trusted(tenant_id='shop',attachment_id=aid,approved=False)
        self.assertIsNone(self.registry.resolve_verified(tenant_id='shop',
            request_id='request1',item='photo',attachment_id=aid))

    def test_other_tenant_cannot_resolve(self):
        aid=self.registry.register_pending(**self.args)
        self.registry.validate_trusted(tenant_id='shop',attachment_id=aid,approved=True)
        self.assertIsNone(self.registry.resolve_verified(tenant_id='other',
            request_id='request1',item='photo',attachment_id=aid))

    def test_other_request_cannot_resolve(self):
        aid=self.registry.register_pending(**self.args)
        self.registry.validate_trusted(tenant_id='shop',attachment_id=aid,approved=True)
        self.assertIsNone(self.registry.resolve_verified(tenant_id='shop',
            request_id='request2',item='photo',attachment_id=aid))

    def test_other_item_cannot_resolve(self):
        aid=self.registry.register_pending(**self.args)
        self.registry.validate_trusted(tenant_id='shop',attachment_id=aid,approved=True)
        self.assertIsNone(self.registry.resolve_verified(tenant_id='shop',
            request_id='request1',item='permission',attachment_id=aid))

    def test_untrusted_type_rejected(self):
        with self.assertRaises(ValueError):
            self.registry.register_pending(**dict(self.args,media_type='application/x-msdownload'))

    def test_bad_hash_rejected(self):
        with self.assertRaises(ValueError):
            self.registry.register_pending(**dict(self.args,sha256='not-a-hash'))

    def test_nonboolean_decision_rejected(self):
        aid=self.registry.register_pending(**self.args)
        with self.assertRaises(ValueError):
            self.registry.validate_trusted(tenant_id='shop',attachment_id=aid,approved=1)

    def test_finalized_attachment_cannot_be_revalidated(self):
        aid=self.registry.register_pending(**self.args)
        self.registry.validate_trusted(tenant_id='shop',attachment_id=aid,approved=False)
        with self.assertRaises(KeyError):
            self.registry.validate_trusted(tenant_id='shop',attachment_id=aid,approved=True)

if __name__=='__main__':unittest.main()
