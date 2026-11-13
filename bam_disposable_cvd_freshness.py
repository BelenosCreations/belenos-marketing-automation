"""CI-only read-only daily.cvd header freshness and digest review.

ClamAV documents a 512-byte CVD header with colon-separated metadata.
These fields and claimed digital-signature bytes are UNTRUSTED without genuine
ClamAV publisher-signature verification and trusted binary provenance. This
module cannot run clamscan, approve staged media, issue evidence or publish.
"""
import datetime
import hashlib
import hmac
import os
import re
import stat

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_U32 = re.compile(r"[0-9a-f]{32}\Z")
_SIGNATURE_TEXT = re.compile(r"[A-Za-z0-9+/=]{16,256}\Z")
_BUILDER = re.compile(r"[A-Za-z0-9_-]{1,40}\Z")
_MIN_FILE_SIZE = 512
_MAX_FILE_SIZE = 256 * 1024 * 1024
_MAX_FRESHNESS_SECONDS = 7 * 86400


def _ci_only():
    if os.environ.get("BAM_EPHEMERAL_PG_TEST") != "1":
        raise PermissionError("CVD header-review canary disabled")


def _parse_header(block, *, now, maximum_age_seconds):
    if type(block) is not bytes or len(block) != 512:
        raise PermissionError("CVD header must occupy exactly 512 bytes")
    # Accept the documented fixed-length ASCII header, not embedded control
    # characters, NULs in fields, or trailing injected metadata.
    stripped = block.rstrip(b"\x00 ")
    if b"\x00" in stripped or any(c < 32 or c > 126 for c in stripped):
        raise PermissionError("Malformed CVD ASCII header")
    try:
        values = stripped.decode("ascii").split(":")
    except UnicodeDecodeError as exc:
        raise PermissionError("Non-ASCII CVD metadata") from None
    if len(values) != 9 or values[0] != "ClamAV-VDB":
        raise PermissionError("Unknown ClamAV CVD header format")
    claimed_date, version, signatures, functionality = values[1:5]
    md5_claim, signature_text, builder, timestamp = values[5:]
    if (not version.isascii() or not version.isdecimal()
            or not 1 <= int(version) <= 1000000000
            or not signatures.isascii() or not signatures.isdecimal()
            or not 1 <= int(signatures) <= 500000000
            or not functionality.isascii() or not functionality.isdecimal()
            or not 1 <= int(functionality) <= 10000
            or _U32.fullmatch(md5_claim) is None
            or _SIGNATURE_TEXT.fullmatch(signature_text) is None
            or _BUILDER.fullmatch(builder) is None
            or not timestamp.isascii() or not timestamp.isdecimal()
            or len(timestamp) > 11):
        raise PermissionError("Malformed untrusted CVD field")
    issued = int(timestamp)
    if not 946684800 <= issued <= 4102444800:
        raise PermissionError("CVD claimed build timestamp is invalid")
    parsed = None
    for fmt in ("%d %b %Y %H:%M %z", "%d %b %Y %H-%M %z"):
        try:
            parsed = datetime.datetime.strptime(claimed_date, fmt)
            break
        except ValueError:
            pass
    if parsed is None or parsed.utcoffset() is None:
        raise PermissionError("CVD human-readable build time invalid")
    if abs(int(parsed.timestamp()) - issued) > 60:
        raise PermissionError("CVD build-time field disagreement")
    if not 0 <= now - issued <= maximum_age_seconds:
        raise PermissionError("Daily signature build time is stale or future-dated")
    return {"claimed_database_version": int(version),
            "claimed_signature_count": int(signatures),
            "claimed_functionality_level": int(functionality),
            "claimed_build_time_utc": issued,
            "claimed_header_age_seconds": now - issued}


def inspect_disposable_daily_cvd_header(*, database_path,
                                        independently_pinned_sha256,
                                        now, maximum_age_seconds):
    """Inspect pinned file bytes and claimed header freshness; no scan occurs."""
    _ci_only()
    if (type(database_path) is not str
            or not os.path.isabs(database_path)
            or os.path.basename(database_path) != "daily.cvd"
            or ".." in database_path.split(os.sep) or "\x00" in database_path):
        raise ValueError("Exact absolute daily.cvd local path required")
    if (type(independently_pinned_sha256) is not str
            or _SHA.fullmatch(independently_pinned_sha256) is None):
        raise ValueError("Independent exact SHA-256 pin required")
    if (type(now) is not int or not 946684800 <= now <= 4102444800
            or type(maximum_age_seconds) is not int
            or not 1 <= maximum_age_seconds <= _MAX_FRESHNESS_SECONDS):
        raise ValueError("Bounded trusted observation clock and policy required")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(database_path, flags)
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        mode = stat.S_IMODE(before.st_mode)
        if (not stat.S_ISREG(before.st_mode)
                or before.st_nlink != 1
                or before.st_uid not in (0, os.getuid())
                or mode & 0o022
                or not _MIN_FILE_SIZE <= before.st_size <= _MAX_FILE_SIZE):
            raise PermissionError("Unsafe local daily.cvd inode")
        digest = hashlib.sha256()
        header = stream.read(512)
        digest.update(header)
        total = len(header)
        while total <= _MAX_FILE_SIZE:
            data = stream.read(min(1024 * 1024, _MAX_FILE_SIZE + 1 - total))
            if not data:
                break
            digest.update(data)
            total += len(data)
        after = os.fstat(stream.fileno())
        if (total != before.st_size or
                (before.st_dev, before.st_ino, before.st_size,
                 before.st_mtime_ns) !=
                (after.st_dev, after.st_ino, after.st_size,
                 after.st_mtime_ns)):
            raise PermissionError("Signature file changed while being inspected")
    if not hmac.compare_digest(digest.hexdigest(), independently_pinned_sha256):
        raise PermissionError("Externally pinned CVD file digest mismatch")
    signals = _parse_header(header, now=now,
                            maximum_age_seconds=maximum_age_seconds)
    return {
        "status": "ci_only_untrusted_cvd_header_freshness_checked",
        **signals,
        "whole_file_matches_caller_pin": True,
        "signature_origin_authenticated": False,
        "embedded_digital_signature_verified": False,
        "actual_clamav_engine_invoked": False,
        "isolated_scanner_worker_proven": False,
        "complete_scanner_database_set_verified": False,
        "scan_evidence_issued": False,
        "media_rights_approved": False,
        "attachment_state_changed": False,
        "production_ready": False,
        "publishing_enabled": False,
    }
