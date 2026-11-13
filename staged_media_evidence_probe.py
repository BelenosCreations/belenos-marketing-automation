"""CI-only read-only bridge from private staged bytes to signed media claims.

This verifies the declared bytes are STILL staged and match their pending
registry row. A signed claim does NOT prove an actual scan or rights review.
There is no attachment approval, audit persistence, HTTP route, or publishing.
"""
import os
import re
import stat

from bam_pending_media_store import BAMPendingMediaStore
from content_upload_preflight import MAX_BYTES
from trusted_media_evidence import OfflineMediaEvidenceGate

_ID = re.compile(r'[0-9a-f]{32}\Z')
_TYPES = frozenset(('image/png', 'image/jpeg', 'image/webp'))


def probe_staged_signed_media(*, store, tenant_id, attachment_id,
                              scan, rights, scanner_key, rights_key, now):
    """Authenticate staged receipt + independent claims without changing state."""
    if os.environ.get('BAM_EPHEMERAL_PG_TEST') != '1':
        raise PermissionError('Disposable offline media evidence probe only')
    if not isinstance(store, BAMPendingMediaStore):
        raise TypeError('Trusted private pending-media store required')
    if (type(tenant_id) is not str or not 0 < len(tenant_id) <= 128
            or tenant_id != tenant_id.strip()
            or type(attachment_id) is not str
            or _ID.fullmatch(attachment_id) is None
            or type(now) is not int or now < 0):
        raise ValueError('Invalid private evidence binding')
    db = store.service.attachments.db
    statement = """SELECT request_id,item,media_type,sha256,status,created_at
                   FROM content_attachments
                   WHERE tenant_id=? AND attachment_id=?"""
    values = (tenant_id, attachment_id)
    row = db.execute(statement, values).fetchone()
    if row is None or row[4] != 'pending' or row[2] not in _TYPES:
        raise KeyError('Current pending image not found')
    request_id, item, media_type, digest, status, created_at = row
    request = store.service.requests.get(
        tenant_id=tenant_id, request_id=request_id)
    if (request is None or request['status'] != 'needs_content'
            or item not in request['required_items']
            or item in request['provided_items']):
        raise PermissionError('Draft no longer accepts this pending media')

    # Reopen the real staging inode rather than trusting the registry SHA alone.
    # Never follow links or read arbitrary user-supplied paths.
    max_bytes = MAX_BYTES[media_type]
    path = store.root / (attachment_id + '.pending')
    try:
        root_info = os.lstat(store.root)
        if (not stat.S_ISDIR(root_info.st_mode)
                or (os.name == 'posix' and
                    stat.S_IMODE(root_info.st_mode) & 0o077)):
            raise PermissionError('Private media directory is unsafe')
        before = os.lstat(path)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or not 0 < before.st_size <= max_bytes
                or (os.name == 'posix' and
                    stat.S_IMODE(before.st_mode) & 0o077)):
            raise PermissionError('Unsafe private staged media inode')
        flags = os.O_RDONLY
        if hasattr(os, 'O_NOFOLLOW'):
            flags |= os.O_NOFOLLOW
        fd = os.open(path, flags)
        with os.fdopen(fd, 'rb') as stream:
            after = os.fstat(stream.fileno())
            if (not stat.S_ISREG(after.st_mode)
                    or after.st_dev != before.st_dev
                    or after.st_ino != before.st_ino
                    or after.st_nlink != 1
                    or after.st_size != before.st_size):
                raise PermissionError('Staged receipt changed during inspection')
            data = stream.read(max_bytes + 1)
    except OSError as exc:
        raise PermissionError('Private staged media unavailable') from None
    store.inspector.inspect(
        content=data, media_type=media_type, expected_sha256=digest)
    pending = dict(attachment_id=attachment_id, tenant_id=tenant_id,
                   request_id=request_id, item=item, media_type=media_type,
                   sha256=digest, status=status, created_at=created_at)
    OfflineMediaEvidenceGate(
        scanner_key=scanner_key, rights_key=rights_key).verify(
            pending=pending, scan=scan, rights=rights,
            channel=request['channel'], now=now)
    if (db.execute(statement, values).fetchone() != row
            or store.service.requests.get(
                tenant_id=tenant_id, request_id=request_id) != request):
        raise PermissionError('Pending media binding changed during inspection')
    return {'status': 'staged_signed_evidence_probe_passed',
            'actual_malware_scan_performed': False,
            'actual_rights_review_performed': False,
            'attachment_state_changed': False,
            'audit_persisted': False,
            'media_verified': False,
            'publishing_enabled': False}
