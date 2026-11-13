"""Read-only disposable local ciphertext retention-inventory audit.

Audits only CI-created private same-host synthetic encrypted archives under
an independently supplied signed recovery-manifest head. Does not decrypt,
delete, rotate keys, authenticate external head custody or verify offsite DR.
"""
import hashlib
import hmac
import os
import stat

from bam_offline_durable_archive import _directory_fd
from bam_offline_recovery_manifest import verify_disposable_recovery_chain
from offline_encrypted_backup import _MAX_ENVELOPE


def audit_disposable_retention_inventory(
        *, directory, chain, expected_head, signer_keys,
        schema_fingerprint, now):
    """Fail closed on unknown, missing, linked, altered or public archives.

    A retention-expired item is an observation, NEVER a deletion instruction.
    No data from the encrypted archives is exposed in the returned report.
    """
    verification = verify_disposable_recovery_chain(
        chain=chain, expected_head=expected_head, signer_keys=signer_keys,
        schema_fingerprint=schema_fingerprint, now=now)
    expected = {entry["archive_name"]: entry for entry in chain}
    directory_fd = _directory_fd(directory)
    retained, expired, byte_count = [], [], 0
    try:
        names = os.listdir(directory_fd)
        if (len(names) != len(expected)
                or set(names) != set(expected)
                or len(names) != len(set(names))):
            raise PermissionError("Archive inventory differs from signed manifest")
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        for name in sorted(expected):
            entry = expected[name]
            fd = os.open(name, flags, dir_fd=directory_fd)
            with os.fdopen(fd, "rb") as stream:
                before = os.fstat(stream.fileno())
                if (not stat.S_ISREG(before.st_mode)
                        or before.st_uid != os.getuid()
                        or before.st_nlink != 1
                        or stat.S_IMODE(before.st_mode) != 0o600
                        or not 0 < before.st_size <= _MAX_ENVELOPE):
                    raise PermissionError("Unsafe private archive inode")
                digest = hashlib.sha256()
                amount = 0
                while True:
                    chunk = stream.read(min(1024 * 1024,
                                            _MAX_ENVELOPE + 1 - amount))
                    if not chunk:
                        break
                    amount += len(chunk)
                    digest.update(chunk)
                    if amount > _MAX_ENVELOPE:
                        raise PermissionError("Oversized encrypted archive")
                after = os.fstat(stream.fileno())
                if (amount != before.st_size
                        or (before.st_dev, before.st_ino, before.st_size,
                            before.st_mtime_ns, before.st_ctime_ns) !=
                           (after.st_dev, after.st_ino, after.st_size,
                            after.st_mtime_ns, after.st_ctime_ns)):
                    raise PermissionError("Archive inode changed during inspection")
            if not hmac.compare_digest(
                    digest.hexdigest(), entry["ciphertext_sha256"]):
                raise PermissionError("Signed ciphertext SHA-256 mismatch")
            byte_count += amount
            if now >= entry["retain_until"]:
                expired.append(name)
            else:
                retained.append(name)
    finally:
        os.close(directory_fd)
    if expired != sorted(verification["expired_archive_names"]):
        raise PermissionError("Manifest retention policy contradiction")
    return {
        "status": "disposable_local_ciphertext_retention_audit_only",
        "signed_manifest_head": verification["head"],
        "verified_archive_count": len(expected),
        "verified_ciphertext_bytes": byte_count,
        "retained_archive_names": retained,
        "expired_archive_names_for_manual_review": expired,
        "unknown_or_missing_files_accepted": False,
        "plaintext_read": False, "encryption_keys_read": False,
        "ciphertext_modified": False, "files_deleted": False,
        "retention_policy_enforced_by_deletion": False,
        "same_host_local_inspection_only": True,
        "independent_head_custody_verified": False,
        "offsite_replica_verified": False,
        "encryption_key_escrow_verified": False,
        "restore_rehearsed_by_this_audit": False,
        "customer_backup_proven": False, "production_ready": False,
        "publishing_enabled": False,
    }
