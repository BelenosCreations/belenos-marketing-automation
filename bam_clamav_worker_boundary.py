"""Inactive, standalone ClamAV CLI execution boundary for private staged media.

Runs no network/download/updater and cannot be reached from BAM HTTP, mark
attachments verified, sign scan claims, establish rights or publish posts.
The caller MUST independently vet the origin of executable/CVD SHA pins and
provide an isolated, least-privilege trusted worker. CI uses mocked subprocess
outcomes and does not prove that genuine ClamAV or its signatures ran.
"""
import hashlib
import hmac
import os
import re
import stat
import subprocess

_ID = re.compile(r"[0-9a-f]{32}\.pending\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_DB_NAMES = frozenset(("daily.cvd", "main.cvd", "bytecode.cvd",
                       "daily.cld", "main.cld", "bytecode.cld"))
_VER = re.compile(r"ClamAV [0-9]+(?:\.[0-9]+){1,3}(?:/[\x20-\x7e]{1,80})?\Z")
_MAX_BINARY = 64 * 1024 * 1024
_MAX_DATABASE = 256 * 1024 * 1024
_MAX_IMAGE = 32 * 1024 * 1024


def _safe_path(path):
    if (type(path) is not str or not os.path.isabs(path)
            or ".." in path.split(os.sep) or "\x00" in path):
        raise ValueError("Independent absolute local path required")
    return path


def _trusted_file_digest(path, expected_sha256, *, limit, executable=False,
                         private=False):
    _safe_path(path)
    if (type(expected_sha256) is not str
            or _SHA.fullmatch(expected_sha256) is None):
        raise ValueError("Independent exact SHA-256 pin required")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        mode = stat.S_IMODE(before.st_mode)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or before.st_uid not in (0, os.getuid())
                or mode & 0o022
                or not 0 < before.st_size <= limit
                or (private and (mode & 0o077))
                or (executable and (not mode & 0o100 or not os.access(path, os.X_OK)))):
            raise PermissionError("Unsafe local scanner/media file inode")
        digest = hashlib.sha256()
        remaining = limit + 1
        size = 0
        while remaining > 0:
            block = stream.read(min(1024 * 1024, remaining))
            if not block:
                break
            size += len(block)
            remaining -= len(block)
            digest.update(block)
        after = os.fstat(stream.fileno())
        if (size != before.st_size
                or (before.st_dev, before.st_ino, before.st_size,
                    before.st_mtime_ns) !=
                   (after.st_dev, after.st_ino, after.st_size,
                    after.st_mtime_ns)):
            raise PermissionError("Scanner/media inode changed during verification")
    if not hmac.compare_digest(digest.hexdigest(), expected_sha256):
        raise PermissionError("Externally pinned scanner/media checksum mismatch")


def _private_media(directory, name, sha256):
    _safe_path(directory)
    if type(name) is not str or _ID.fullmatch(name) is None:
        raise ValueError("Exact private staged filename required")
    flags = os.O_RDONLY | os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(directory, flags)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISDIR(info.st_mode)
                or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o700):
            raise PermissionError("Private staged media directory required")
    finally:
        os.close(fd)
    path = os.path.join(directory, name)
    _trusted_file_digest(path, sha256, limit=_MAX_IMAGE, private=True)
    return path


def _run_clamav(cmd, *, timeout):
    try:
        outcome = subprocess.run(
            cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=timeout, check=False,
            close_fds=True, cwd="/",
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C"},
            start_new_session=True)
    except (subprocess.TimeoutExpired, OSError) as exc:
        raise PermissionError("Trusted local scanner invocation unavailable") from None
    if (type(outcome.stdout) is not bytes or len(outcome.stdout) > 8192
            or type(outcome.stderr) is not bytes or len(outcome.stderr) > 8192):
        raise PermissionError("Unbounded scanner response")
    return outcome


def scan_disposable_clamav_candidate(*, executable_path, database_path,
                                     staged_directory, staged_name,
                                     executable_sha256, database_sha256,
                                     staged_sha256):
    """Invoke installed ClamAV only in an explicit CI/offline worker context.

    Return a *candidate* verdict, not a signed scan, rights evidence,
    trusted source identity, sandbox attestation or media authorization.
    """
    if os.environ.get("BAM_EPHEMERAL_PG_TEST") != "1":
        raise PermissionError("Local-only dormant scanner worker boundary")
    _safe_path(executable_path)
    _safe_path(database_path)
    if (os.path.basename(executable_path) != "clamscan"
            or os.path.basename(database_path) not in _DB_NAMES):
        raise PermissionError("Only exact ClamAV CLI and known signature file permitted")
    _trusted_file_digest(executable_path, executable_sha256,
                         limit=_MAX_BINARY, executable=True)
    _trusted_file_digest(database_path, database_sha256,
                         limit=_MAX_DATABASE)
    path = _private_media(staged_directory, staged_name, staged_sha256)
    version_response = _run_clamav([executable_path, "--version"], timeout=5)
    if version_response.returncode != 0:
        raise PermissionError("ClamAV version probe failed")
    try:
        version = version_response.stdout.decode("ascii").strip()
    except UnicodeError as exc:
        raise PermissionError("Malformed ClamAV version result") from None
    if _VER.fullmatch(version) is None:
        raise PermissionError("Unexpected ClamAV version output")
    report = _run_clamav([
        executable_path, "--no-summary", "--stdout",
        "--database=" + database_path, "--", path], timeout=45)
    # ClamAV CLI return codes: 0 no detections, 1 detections, 2+ errors.
    if report.returncode not in (0, 1):
        raise PermissionError("ClamAV scan failed; never infer clean")
    # Detect changes during scanning; no worker isolation/TOCTOU guarantees
    # are supplied by this offline experiment.
    _trusted_file_digest(executable_path, executable_sha256,
                         limit=_MAX_BINARY, executable=True)
    _trusted_file_digest(database_path, database_sha256,
                         limit=_MAX_DATABASE)
    _private_media(staged_directory, staged_name, staged_sha256)
    return {
        "status": "offline_clamav_cli_candidate_unapproved",
        "candidate_verdict": "clean" if report.returncode == 0 else "infected",
        "claimed_version": version,
        "scanner_process_invoked": True,
        "executable_digest_matches_external_pin": True,
        "database_digest_matches_external_pin": True,
        "staged_digest_matches_external_pin": True,
        "origin_of_external_pins_verified": False,
        "trusted_worker_isolation_proven": False,
        "genuine_engine_execution_proven_in_ci": False,
        "legal_rights_review_performed": False,
        "signed_scan_evidence_issued": False,
        "attachment_status_changed": False,
        "media_approval_allowed": False,
        "production_ready": False, "publishing_enabled": False,
    }
