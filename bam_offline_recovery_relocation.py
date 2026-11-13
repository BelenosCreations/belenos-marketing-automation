"""CI-only ciphertext relocation and original-site-loss recovery rehearsal.

This copies bounded *synthetic* encrypted bytes between two private local
directories, after independently pinned signed-manifest verification.
It is NOT an offsite backup, key escrow, production replica, PITR or DR system.
No plaintext or encryption key enters the relocation operation.
"""
import hashlib
import hmac
import os
import stat

from bam_offline_durable_archive import _directory_fd, _guard
from bam_offline_recovery_manifest import verify_disposable_recovery_chain
from offline_encrypted_backup import _MAX_ENVELOPE


def relocate_disposable_ciphertext(*, source_directory, destination_directory,
                                   archive_name, chain, expected_head,
                                   signer_keys, schema_fingerprint, now):
    """Copy one pinned ciphertext envelope, atomically and without replacement.

    The caller supplies the signer keyring and latest-head pin independently.
    Only a later separately keyed AES-GCM restore can prove recoverability.
    """
    _guard(archive_name)
    checked = verify_disposable_recovery_chain(
        chain=chain, expected_head=expected_head, signer_keys=signer_keys,
        schema_fingerprint=schema_fingerprint, now=now)
    entries = [item for item in chain if item["archive_name"] == archive_name]
    if len(entries) != 1:
        raise KeyError("Requested recovery point absent from signed manifest")
    entry = entries[0]
    if now >= entry["retain_until"]:
        raise PermissionError("Expired recovery point cannot be relocated")
    src = _directory_fd(source_directory)
    try:
        dst = _directory_fd(destination_directory)
        try:
            s, d = os.fstat(src), os.fstat(dst)
            if (s.st_dev, s.st_ino) == (d.st_dev, d.st_ino):
                raise PermissionError("Independent private replica directory required")
            flags = os.O_RDONLY
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            fd = os.open(archive_name, flags, dir_fd=src)
            with os.fdopen(fd, "rb") as stream:
                before = os.fstat(stream.fileno())
                if (not stat.S_ISREG(before.st_mode)
                        or before.st_uid != os.getuid()
                        or before.st_nlink != 1
                        or stat.S_IMODE(before.st_mode) != 0o600
                        or not 0 < before.st_size <= _MAX_ENVELOPE):
                    raise PermissionError("Unsafe private source ciphertext inode")
                ciphertext = stream.read(_MAX_ENVELOPE + 1)
                after = os.fstat(stream.fileno())
                if (len(ciphertext) != before.st_size
                        or (before.st_dev, before.st_ino, before.st_size,
                            before.st_mtime_ns) !=
                           (after.st_dev, after.st_ino, after.st_size,
                            after.st_mtime_ns)):
                    raise PermissionError("Ciphertext changed during read")
            digest = hashlib.sha256(ciphertext).hexdigest()
            if not hmac.compare_digest(digest, entry["ciphertext_sha256"]):
                raise PermissionError("Signed ciphertext digest mismatch")
            stage = ".stage-" + os.urandom(16).hex()
            write_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                write_flags |= os.O_NOFOLLOW
            opened = os.open(stage, write_flags, 0o600, dir_fd=dst)
            try:
                with os.fdopen(opened, "wb") as out:
                    out.write(ciphertext)
                    out.flush()
                    os.fsync(out.fileno())
                os.link(stage, archive_name, src_dir_fd=dst, dst_dir_fd=dst,
                        follow_symlinks=False)
                os.unlink(stage, dir_fd=dst)
                os.fsync(dst)
            finally:
                try:
                    os.unlink(stage, dir_fd=dst)
                except FileNotFoundError:
                    pass
            return {
                "status": "disposable_local_ciphertext_copy_persisted",
                "archive_name": archive_name,
                "ciphertext_sha256": digest,
                "signed_manifest_head": checked["head"],
                "copied_bytes": len(ciphertext),
                "same_host_local_rehearsal": True,
                "source_ciphertext_deleted": False,
                "local_replica_recovery_verified": False,
                "offsite_replica_verified": False,
                "independent_head_custody_verified": False,
                "key_escrow_verified": False,
                "retention_deletion_executed": False,
                "production_backup_ready": False,
                "publishing_enabled": False}
        finally:
            os.close(dst)
    finally:
        os.close(src)
