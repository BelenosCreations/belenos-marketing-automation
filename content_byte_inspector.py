"""Offline byte validation for BAM content attachments.

This module does NOT scan for malware, validate consent, or handle uploads.
A trusted caller must obtain bytes from private storage and verify them here.
"""
import hashlib
import hmac
from content_upload_preflight import MAX_BYTES

SIGNATURES={
    'image/png':(b'\x89PNG\r\n\x1a\n',),
    'image/jpeg':(b'\xff\xd8\xff',),
    'image/webp':(b'RIFF',),
    'application/pdf':(b'%PDF-',),
}

class AttachmentByteInspector:
    def __init__(self, registry):
        self.registry=registry

    @staticmethod
    def inspect(*, content, media_type, expected_sha256):
        if media_type not in MAX_BYTES:
            raise ValueError('Unsupported media type')
        if not isinstance(content,bytes) or not 0<len(content)<=MAX_BYTES[media_type]:
            raise ValueError('Empty, invalid or oversized attachment bytes')
        if (not isinstance(expected_sha256,str) or len(expected_sha256)!=64
                or any(c not in '0123456789abcdef' for c in expected_sha256)):
            raise ValueError('Invalid expected digest')
        digest=hashlib.sha256(content).hexdigest()
        if not hmac.compare_digest(digest,expected_sha256):
            raise ValueError('Attachment hash mismatch')
        if media_type in SIGNATURES and not any(
                content.startswith(sig) for sig in SIGNATURES[media_type]):
            raise ValueError('Attachment signature does not match declared type')
        if media_type=='image/webp' and content[8:12]!=b'WEBP':
            raise ValueError('Invalid WebP signature')
        if media_type=='video/mp4' and (len(content)<12 or content[4:8]!=b'ftyp'):
            raise ValueError('Invalid MP4 signature')
        if media_type=='text/plain':
            try:
                content.decode('utf-8')
            except UnicodeDecodeError as exc:
                raise ValueError('Text must be valid UTF-8') from exc
        return digest

    def inspect_pending(self, *, tenant_id, attachment_id, content):
        """Inspect only; NEVER auto-approve. Scanner/consent still required."""
        row=self.registry.db.execute("""SELECT media_type,sha256 FROM content_attachments
            WHERE tenant_id=? AND attachment_id=? AND status='pending'""",
            (tenant_id,attachment_id)).fetchone()
        if row is None:
            raise KeyError('Pending attachment not found')
        return self.inspect(content=content,media_type=row[0],expected_sha256=row[1])
