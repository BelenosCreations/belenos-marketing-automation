"""Offline attachment-format sanity checks; NEVER an anti-malware scanner.

Validate a matching SHA-256 and conservative container structure without
decoding active content. Rights, consent, storage authenticity, malware and
publication approval MUST be independently checked by a trusted service.
"""
import hashlib
import hmac
import struct
import zlib
from content_upload_preflight import MAX_BYTES

PNG_MAGIC=b'\x89PNG\r\n\x1a\n'


def _check_png(data):
    if not data.startswith(PNG_MAGIC):
        raise ValueError('Invalid PNG signature')
    pos=8
    seen_ihdr=False
    seen_idat=False
    count=0
    while pos<len(data):
        count+=1
        if count>4096 or pos+12>len(data):
            raise ValueError('Invalid PNG chunk boundary')
        size=struct.unpack_from('>I',data,pos)[0]
        end=pos+12+size
        if end>len(data):
            raise ValueError('Truncated PNG chunk')
        kind=data[pos+4:pos+8]
        payload=data[pos+8:pos+8+size]
        crc=struct.unpack_from('>I',data,pos+8+size)[0]
        if zlib.crc32(kind+payload)&0xffffffff!=crc:
            raise ValueError('Invalid PNG chunk checksum')
        if not seen_ihdr:
            if kind!=b'IHDR' or size!=13:
                raise ValueError('Missing first PNG header')
            width,height=struct.unpack_from('>II',payload)
            if not 0<width<=20000 or not 0<height<=20000:
                raise ValueError('Invalid PNG dimensions')
            seen_ihdr=True
        elif kind==b'IHDR':
            raise ValueError('Repeated PNG header')
        if kind==b'IDAT':
            seen_idat=True
        if kind==b'IEND':
            if size!=0 or not seen_idat or end!=len(data):
                raise ValueError('Incomplete or trailing PNG data')
            return
        pos=end
    raise ValueError('PNG missing end chunk')


def _check_webp(data):
    if len(data)<20 or data[:4]!=b'RIFF' or data[8:12]!=b'WEBP':
        raise ValueError('Invalid WebP signature')
    if struct.unpack_from('<I',data,4)[0]!=len(data)-8:
        raise ValueError('Invalid WebP RIFF size')
    pos=12
    count=0
    image_chunk=False
    while pos<len(data):
        count+=1
        if count>4096 or pos+8>len(data):
            raise ValueError('Invalid WebP chunk boundary')
        kind=data[pos:pos+4]
        size=struct.unpack_from('<I',data,pos+4)[0]
        end=pos+8+size+(size%2)
        if end>len(data):
            raise ValueError('Truncated WebP chunk')
        if count==1 and kind not in (b'VP8 ',b'VP8L',b'VP8X'):
            raise ValueError('Invalid WebP image header')
        image_chunk=image_chunk or kind in (b'VP8 ',b'VP8L',b'ANMF')
        pos=end
    if pos!=len(data) or not image_chunk:
        raise ValueError('WebP missing image payload')


def _check_mp4(data):
    pos=0
    count=0
    kinds=set()
    while pos<len(data):
        count+=1
        if count>4096 or pos+8>len(data):
            raise ValueError('Invalid MP4 box boundary')
        size=struct.unpack_from('>I',data,pos)[0]
        kind=data[pos+4:pos+8]
        header=8
        if size==1:
            if pos+16>len(data):
                raise ValueError('Truncated extended MP4 box')
            size=struct.unpack_from('>Q',data,pos+8)[0]
            header=16
        if size<header or pos+size>len(data):
            raise ValueError('Invalid MP4 box size')
        if count==1 and (kind!=b'ftyp' or size<header+8):
            raise ValueError('Invalid MP4 ftyp box')
        kinds.add(kind)
        pos+=size
    if not {b'ftyp',b'moov',b'mdat'}.issubset(kinds):
        raise ValueError('MP4 missing required container boxes')


def _check_container(data,media_type):
    if media_type=='image/png':
        _check_png(data)
    elif media_type=='image/webp':
        _check_webp(data)
    elif media_type=='image/jpeg':
        if len(data)<12 or not data.startswith(b'\xff\xd8\xff') or not data.endswith(b'\xff\xd9'):
            raise ValueError('Incomplete JPEG container')
    elif media_type=='video/mp4':
        _check_mp4(data)
    elif media_type=='application/pdf':
        if not data.startswith(b'%PDF-') or b'%%EOF' not in data[-2048:]:
            raise ValueError('Incomplete PDF container')
    elif media_type=='text/plain':
        try:
            data.decode('utf-8')
        except UnicodeDecodeError as exc:
            raise ValueError('Text must be valid UTF-8') from exc


class AttachmentByteInspector:
    def __init__(self, registry):
        self.registry=registry

    @staticmethod
    def inspect(*, content, media_type, expected_sha256):
        if media_type not in MAX_BYTES:
            raise ValueError('Unsupported media type')
        if type(content) is not bytes or not 0<len(content)<=MAX_BYTES[media_type]:
            raise ValueError('Empty, invalid or oversized attachment bytes')
        if (type(expected_sha256) is not str or len(expected_sha256)!=64
                or any(c not in '0123456789abcdef' for c in expected_sha256)):
            raise ValueError('Invalid expected digest')
        digest=hashlib.sha256(content).hexdigest()
        if not hmac.compare_digest(digest,expected_sha256):
            raise ValueError('Attachment hash mismatch')
        _check_container(content,media_type)
        return digest

    def inspect_pending(self, *, tenant_id, attachment_id, content):
        """Inspect only; NEVER auto-approve. Scanner/consent still required."""
        row=self.registry.db.execute("""SELECT media_type,sha256 FROM content_attachments
            WHERE tenant_id=? AND attachment_id=? AND status='pending'""",
            (tenant_id,attachment_id)).fetchone()
        if row is None:
            raise KeyError('Pending attachment not found')
        return self.inspect(content=content,media_type=row[0],expected_sha256=row[1])
