"""Disposable CI ciphertext-archive experiment; NOT a production backup service.

A trusted, owner-only absolute 0700 directory receives immutable 0600
authenticated *synthetic* AES-GCM envelopes. Uses fsync and atomic link
publication to prevent replacement. Retention, offsite transfer, key escrow,
large streaming archives and production PostgreSQL restore are NOT provided.
"""
import hashlib
import hmac
import os
import re
import stat

from offline_encrypted_backup import (
    _MAX_ENVELOPE, open_disposable_backup)

_NAME = re.compile(r'[a-z][a-z0-9_-]{0,47}\.bamenc\Z')
_SHA = re.compile(r'[0-9a-f]{64}\Z')


def _guard(name):
    if os.environ.get('BAM_EPHEMERAL_PG_TEST') != '1':
        raise PermissionError('Only disposable CI archive rehearsal permitted')
    if type(name) is not str or _NAME.fullmatch(name) is None:
        raise ValueError('Unsafe disposable archive name')


def _directory_fd(directory):
    if (type(directory) is not str or not os.path.isabs(directory)
            or '..' in directory.split(os.sep)):
        raise ValueError('Trusted absolute archive directory required')
    flags = os.O_RDONLY | os.O_DIRECTORY
    if hasattr(os, 'O_NOFOLLOW'):
        flags |= os.O_NOFOLLOW
    fd = os.open(directory, flags)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISDIR(info.st_mode) or
                stat.S_IMODE(info.st_mode) != 0o700 or
                info.st_uid != os.getuid()):
            raise PermissionError('Archive directory is not private')
        return fd
    except BaseException:
        os.close(fd)
        raise


def store_disposable_ciphertext(*, directory, name, envelope, root_key,
                                 schema_fingerprint, now):
    """Authenticate synthetic envelope then durably commit ciphertext only.

    The caller must preserve the returned ciphertext SHA-256 independently.
    It is not an escrow, full-volume backup or offsite replication service.
    """
    _guard(name)
    if type(envelope) is not bytes or not 0 < len(envelope) <= _MAX_ENVELOPE:
        raise ValueError('Invalid bounded ciphertext envelope')
    open_disposable_backup(envelope=envelope, root_key=root_key,
        expected_schema_fingerprint=schema_fingerprint, now=now)
    digest = hashlib.sha256(envelope).hexdigest()
    dirfd = _directory_fd(directory)
    stage = '.stage-' + os.urandom(16).hex()
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, 'O_NOFOLLOW'):
            flags |= os.O_NOFOLLOW
        fd = os.open(stage, flags, 0o600, dir_fd=dirfd)
        try:
            with os.fdopen(fd, 'wb', closefd=True) as writer:
                writer.write(envelope)
                writer.flush()
                os.fsync(writer.fileno())
            # Never replace an existing archive or follow a destination link.
            os.link(stage, name, src_dir_fd=dirfd, dst_dir_fd=dirfd,
                    follow_symlinks=False)
            os.unlink(stage, dir_fd=dirfd)
            os.fsync(dirfd)
        finally:
            try:
                os.unlink(stage, dir_fd=dirfd)
            except FileNotFoundError:
                pass
    finally:
        os.close(dirfd)
    return {'status': 'disposable_ciphertext_archived',
            'archive_name': name, 'ciphertext_sha256': digest,
            'bytes_on_disk': len(envelope), 'plaintext_written': False,
            'key_written': False, 'offsite_copy_verified': False,
            'retention_activated': False, 'production_ready': False}


def restore_disposable_ciphertext(*, directory, name, root_key,
                                   schema_fingerprint, now,
                                   expected_ciphertext_sha256):
    """Check independent SHA pin and inode before returning decrypted bytes."""
    _guard(name)
    if (type(expected_ciphertext_sha256) is not str
            or _SHA.fullmatch(expected_ciphertext_sha256) is None):
        raise ValueError('Independent ciphertext hash pin required')
    dirfd = _directory_fd(directory)
    try:
        flags = os.O_RDONLY
        if hasattr(os, 'O_NOFOLLOW'):
            flags |= os.O_NOFOLLOW
        fd = os.open(name, flags, dir_fd=dirfd)
        with os.fdopen(fd, 'rb') as reader:
            before = os.fstat(reader.fileno())
            if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                    or stat.S_IMODE(before.st_mode) != 0o600
                    or before.st_uid != os.getuid()
                    or not 0 < before.st_size <= _MAX_ENVELOPE):
                raise PermissionError('Unsafe disposable archive inode')
            envelope = reader.read(_MAX_ENVELOPE + 1)
            after = os.fstat(reader.fileno())
            if (before.st_size != len(envelope) or
                    before.st_dev != after.st_dev or
                    before.st_ino != after.st_ino or
                    before.st_size != after.st_size or
                    before.st_mtime_ns != after.st_mtime_ns):
                raise PermissionError('Archive changed during read')
    finally:
        os.close(dirfd)
    if not hmac.compare_digest(
            hashlib.sha256(envelope).hexdigest(), expected_ciphertext_sha256):
        raise PermissionError('Pinned ciphertext mismatch')
    return open_disposable_backup(
        envelope=envelope, root_key=root_key,
        expected_schema_fingerprint=schema_fingerprint, now=now)
