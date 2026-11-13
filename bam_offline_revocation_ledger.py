"""CI-only filesystem-backed append-only revocation audit rehearsal.

Events remain independently HMAC chained by trusted_media_revocation. This
module persists *synthetic* signed event objects in a private directory using
atomic no-replace publication + fsync. The caller MUST separately and durably
pin the newest head outside this directory. A real tenant-key service,
operator identity, scan/right verification and production audit do not exist.
"""
import fcntl
import json
import os
import re
import stat

from bam_offline_durable_archive import _directory_fd
from trusted_media_revocation import (
    append_revocation_event, verify_revocation_chain)

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_RECORD = re.compile(r"rev-[0-9]{6}\.json\Z")
_MAX_EVENT_BYTES = 2048
_MAX_EVENTS = 256


def _guard(expected_head, now):
    if os.environ.get("BAM_EPHEMERAL_PG_TEST") != "1":
        raise PermissionError("Only disposable local revocation audit rehearsal permitted")
    if (type(expected_head) is not str or _SHA.fullmatch(expected_head) is None
            or type(now) is not int or now < 0):
        raise ValueError("Independent current-head pin and operator clock required")


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode("ascii")


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate serialized audit property")
        result[key] = value
    return result


def _read_records(dirfd):
    names = os.listdir(dirfd)
    if (len(names) > _MAX_EVENTS or
            any(_RECORD.fullmatch(name) is None for name in names)):
        raise PermissionError("Unexpected files in private audit directory")
    names.sort()
    if names != [f"rev-{n:06d}.json" for n in range(1, len(names) + 1)]:
        raise PermissionError("Revocation sequence missing, repeated or reordered")
    records = []
    for name in names:
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(name, flags, dir_fd=dirfd)
        with os.fdopen(fd, "rb") as reader:
            before = os.fstat(reader.fileno())
            if (not stat.S_ISREG(before.st_mode)
                    or before.st_nlink != 1
                    or before.st_uid != os.getuid()
                    or stat.S_IMODE(before.st_mode) != 0o600
                    or not 0 < before.st_size <= _MAX_EVENT_BYTES):
                raise PermissionError("Unsafe private revocation event inode")
            raw = reader.read(_MAX_EVENT_BYTES + 1)
            after = os.fstat(reader.fileno())
            if (len(raw) != before.st_size
                    or before.st_ino != after.st_ino
                    or before.st_dev != after.st_dev
                    or before.st_size != after.st_size
                    or before.st_mtime_ns != after.st_mtime_ns):
                raise PermissionError("Revocation event changed during read")
        try:
            event = json.loads(raw.decode("ascii"), object_pairs_hook=_unique_pairs)
        except (ValueError, UnicodeError) as exc:
            raise PermissionError("Malformed private revocation audit event") from exc
        if type(event) is not dict or _canonical(event) != raw:
            raise PermissionError("Noncanonical private revocation audit event")
        records.append(event)
    if sorted(os.listdir(dirfd)) != names:
        raise PermissionError("Private revocation directory changed during read")
    return tuple(records)


def load_disposable_revocation_audit(*, directory, audit_key, expected_head, now):
    """Read entire private event log and verify the independently pinned head."""
    _guard(expected_head, now)
    fd = _directory_fd(directory)
    try:
        fcntl.flock(fd, fcntl.LOCK_SH)
        chain = _read_records(fd)
        verified = verify_revocation_chain(
            chain=chain, audit_key=audit_key, expected_head=expected_head,
            now=now)
        return chain, {"status": "offline_persisted_revocation_audit_verified",
                       "event_count": verified["event_count"],
                       "head": verified["head"],
                       "disk_events_read": len(chain),
                       "external_latest_head_persisted": False,
                       "production_audit_ready": False,
                       "actual_scanning_performed": False,
                       "publishing_enabled": False}
    finally:
        os.close(fd)


def append_disposable_revocation_audit(*, directory, audit_key,
                                       expected_head, claim, kind,
                                       reason, now):
    """Append one signed event via no-replace file publication and fsync.

    A mismatched prior head, any corrupted/missing record, or concurrent
    competing append fails closed. Caller must publish new pin independently.
    """
    _guard(expected_head, now)
    fd = _directory_fd(directory)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        chain = _read_records(fd)
        verify_revocation_chain(
            chain=chain, audit_key=audit_key, expected_head=expected_head,
            now=now)
        updated, new_head = append_revocation_event(
            chain=chain, expected_head=expected_head, audit_key=audit_key,
            claim=claim, kind=kind, reason=reason, now=now)
        name = f"rev-{len(updated):06d}.json"
        payload = _canonical(updated[-1])
        if not 0 < len(payload) <= _MAX_EVENT_BYTES:
            raise PermissionError("Revocation record exceeds local size limit")
        stage = ".stage-" + os.urandom(16).hex()
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        opened = os.open(stage, flags, 0o600, dir_fd=fd)
        try:
            with os.fdopen(opened, "wb") as writer:
                writer.write(payload)
                writer.flush()
                os.fsync(writer.fileno())
            os.link(stage, name, src_dir_fd=fd, dst_dir_fd=fd,
                    follow_symlinks=False)
            os.unlink(stage, dir_fd=fd)
            os.fsync(fd)
        finally:
            try:
                os.unlink(stage, dir_fd=fd)
            except FileNotFoundError:
                pass
        reloaded = _read_records(fd)
        verify_revocation_chain(
            chain=reloaded, audit_key=audit_key, expected_head=new_head,
            now=now)
        if reloaded != updated:
            raise PermissionError("Persistent audit did not match append")
        return {"status": "disposable_revocation_event_durably_appended",
                "head": new_head, "event_count": len(updated),
                "event_written_locally": True,
                "external_latest_head_persisted": False,
                "authoritative_tenant_log_implemented": False,
                "rights_review_performed": False,
                "malware_scanning_performed": False,
                "production_ready": False,
                "publishing_enabled": False}
    finally:
        os.close(fd)
