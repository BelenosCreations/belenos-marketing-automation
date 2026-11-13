import hashlib
import sqlite3
import unittest
from content_attachments import AttachmentRegistry
from content_byte_inspector import AttachmentByteInspector

class ByteInspectorTests(unittest.TestCase):
    @staticmethod
    def _chunk(kind,payload):
        import zlib
        return (len(payload).to_bytes(4,'big')+kind+payload+
                (zlib.crc32(kind+payload)&0xffffffff).to_bytes(4,'big'))

    def setUp(self):
        self.registry=AttachmentRegistry(sqlite3.connect(':memory:'))
        self.inspector=AttachmentByteInspector(self.registry)
        self.png=(b'\\x89PNG\\r\\n\\x1a\\n' +
            self._chunk(b'IHDR',__import__('struct').pack('>IIBBBBB',
                1,1,8,6,0,0,0)) +
            self._chunk(b'IDAT',__import__('zlib').compress(
                b'\\x00\\xff\\x00\\x00\\xff')) +
            self._chunk(b'IEND',b''))
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


    def test_corrupted_png_crc_truncated_and_extra_bytes_fail(self):
        for sample in (self.png[:-1],
                       self.png+b'extra',
                       self.png[:45]+bytes([self.png[45]^1])+self.png[46:],
                       b'\\x89PNG\\r\\n\\x1a\\n'+b'test-data'):
            with self.subTest(size=len(sample)):
                with self.assertRaises(ValueError):
                    self.inspector.inspect(content=sample,media_type='image/png',
                        expected_sha256=hashlib.sha256(sample).hexdigest())

    def test_riff_length_and_mp4_box_boundaries_fail(self):
        samples=(
            ('image/webp',b'RIFF'+(100).to_bytes(4,'little')+b'WEBPVP8 '+b'\\x00'*8),
            ('video/mp4',b'\\x00\\x00\\x00\\x10ftypisom0000'),
            ('video/mp4',b'\\x00\\x00\\x00\\x00ftypisom0000'),
        )
        for media_type,data in samples:
            with self.subTest(media_type=media_type):
                with self.assertRaises(ValueError):
                    self.inspector.inspect(content=data,media_type=media_type,
                        expected_sha256=hashlib.sha256(data).hexdigest())

    def test_incomplete_pdf_and_jpeg_fail_even_with_matching_digest(self):
        for media_type,data in (
            ('application/pdf',b'%PDF-1.7\\nobjects only'),
            ('image/jpeg',b'\\xff\\xd8\\xff not finished')):
            with self.assertRaises(ValueError):
                self.inspector.inspect(content=data,media_type=media_type,
                    expected_sha256=hashlib.sha256(data).hexdigest())

if __name__=='__main__':unittest.main()
