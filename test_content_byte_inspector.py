import hashlib
import sqlite3
import unittest
from content_attachments import AttachmentRegistry
from content_byte_inspector import AttachmentByteInspector

class ByteInspectorTests(unittest.TestCase):
    def setUp(self):
        self.registry=AttachmentRegistry(sqlite3.connect(':memory:'))
        self.inspector=AttachmentByteInspector(self.registry)
        self.png=b'\x89PNG\r\n\x1a\n' + b'test-data'
        self.digest=hashlib.sha256(self.png).hexdigest()

    def test_valid_png_bytes(self):
        self.assertEqual(self.inspector.inspect(content=self.png,
            media_type='image/png',expected_sha256=self.digest),self.digest)

    def test_mismatched_hash_rejected(self):
        with self.assertRaises(ValueError):
            self.inspector.inspect(content=self.png,media_type='image/png',
                expected_sha256='0'*64)

    def test_wrong_signature_rejected(self):
        data=b'not-a-png'
        with self.assertRaises(ValueError):
            self.inspector.inspect(content=data,media_type='image/png',
                expected_sha256=hashlib.sha256(data).hexdigest())

    def test_webp_signature_rejected(self):
        data=b'RIFF1234WRONG'
        with self.assertRaises(ValueError):
            self.inspector.inspect(content=data,media_type='image/webp',
                expected_sha256=hashlib.sha256(data).hexdigest())

    def test_mp4_signature_rejected(self):
        data=b'not-an-mp4!'
        with self.assertRaises(ValueError):
            self.inspector.inspect(content=data,media_type='video/mp4',
                expected_sha256=hashlib.sha256(data).hexdigest())

    def test_invalid_utf8_rejected(self):
        data=b'\xff\xfe'
        with self.assertRaises(ValueError):
            self.inspector.inspect(content=data,media_type='text/plain',
                expected_sha256=hashlib.sha256(data).hexdigest())

    def test_empty_bytes_rejected(self):
        with self.assertRaises(ValueError):
            self.inspector.inspect(content=b'',media_type='image/png',
                expected_sha256=hashlib.sha256(b'').hexdigest())

    def test_pending_inspection_does_not_verify(self):
        aid=self.registry.register_pending(tenant_id='shop',request_id='r1',
            item='photo',media_type='image/png',sha256=self.digest,
            storage_key='private/key',now=100)
        self.assertEqual(self.inspector.inspect_pending(tenant_id='shop',
            attachment_id=aid,content=self.png),self.digest)
        self.assertIsNone(self.registry.resolve_verified(tenant_id='shop',
            request_id='r1',item='photo',attachment_id=aid))

    def test_other_tenant_cannot_inspect(self):
        aid=self.registry.register_pending(tenant_id='shop',request_id='r1',
            item='photo',media_type='image/png',sha256=self.digest,
            storage_key='private/key',now=100)
        with self.assertRaises(KeyError):
            self.inspector.inspect_pending(tenant_id='other',
                attachment_id=aid,content=self.png)

    def test_rejected_attachment_cannot_inspect(self):
        aid=self.registry.register_pending(tenant_id='shop',request_id='r1',
            item='photo',media_type='image/png',sha256=self.digest,
            storage_key='private/key',now=100)
        self.registry.validate_trusted(tenant_id='shop',attachment_id=aid,approved=False)
        with self.assertRaises(KeyError):
            self.inspector.inspect_pending(tenant_id='shop',
                attachment_id=aid,content=self.png)

if __name__=='__main__':unittest.main()
