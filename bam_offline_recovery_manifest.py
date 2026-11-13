"""CI-only signed recovery manifest and externally controlled key-rotation rehearsal.

The durable ciphertext writer remains separate. No key, plaintext, recovery
manifest or authoritative head is persisted here, and retention/offsite
replication is never performed. Production, hosted services and deletion
remain disabled.
"""
import hashlib
import hmac
import json
import os
import re

from bam_offline_durable_archive import restore_disposable_ciphertext

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_NAME = re.compile(r"[a-z][a-z0-9_-]{0,47}\.bamenc\Z")
_ID = re.compile(r"[a-z][a-z0-9_-]{0,31}\Z")
_ZERO = "0" * 64
_MAX_MANIFESTS = 32
_MAX_RETENTION = 366 * 86400
_FIELDS = frozenset(("format", "sequence", "issued_at", "retain_until",
                     "archive_name", "ciphertext_sha256", "schema_sha256",
                     "encryption_key_id", "signer_key_id", "previous_head",
                     "mac"))
_FORMAT = "bam-disposable-recovery-manifest-v1"


def _sha(value):
    return type(value) is str and _SHA.fullmatch(value) is not None


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode("ascii")


def _guard(schema_fingerprint, now):
    if os.environ.get("BAM_EPHEMERAL_PG_TEST") != "1":
        raise PermissionError("Only disposable offline recovery rehearsal permitted")
    if not _sha(schema_fingerprint) or type(now) is not int or now < 0:
        raise ValueError("Pinned offline schema and operator clock required")


def _signers(keys):
    if type(keys) is not dict or not 1 <= len(keys) <= 8:
        raise ValueError("External signer keyring required")
    values = []
    for name, key in keys.items():
        if (type(name) is not str or _ID.fullmatch(name) is None
                or type(key) is not bytes or len(key) != 32):
            raise ValueError("Invalid independently managed signer key")
        if any(hmac.compare_digest(key, old) for old in values):
            raise ValueError("Signer key material reused across IDs")
        values.append(key)


def _mac(entry, key):
    return hmac.new(key, _canonical({k: v for k, v in entry.items()
                                      if k != "mac"}), hashlib.sha256).hexdigest()


def _head(entry):
    return hashlib.sha256(_canonical(entry)).hexdigest()


def verify_disposable_recovery_chain(*, chain, expected_head, signer_keys,
                                     schema_fingerprint, now):
    """Verify each signed entry against a separately obtained newest-head pin.

    A caller-controlled zero pin cannot establish that no prior recovery
    points existed; operational custody of the pin is a separate prerequisite.
    """
    _guard(schema_fingerprint, now)
    _signers(signer_keys)
    if (not _sha(expected_head) or type(chain) not in (tuple, list)
            or len(chain) > _MAX_MANIFESTS):
        raise ValueError("Bounded independently pinned chain required")
    previous, previous_time = _ZERO, -1
    names, digests, expired = set(), set(), []
    for index, entry in enumerate(chain, 1):
        if type(entry) is not dict or set(entry) != _FIELDS:
            raise PermissionError("Recovery manifest shape is invalid")
        key_id = entry["signer_key_id"]
        kid = entry["encryption_key_id"]
        issued, until = entry["issued_at"], entry["retain_until"]
        name, digest = entry["archive_name"], entry["ciphertext_sha256"]
        if (entry["format"] != _FORMAT
                or type(entry["sequence"]) is not int
                or entry["sequence"] != index
                or type(issued) is not int or not previous_time <= issued <= now
                or type(until) is not int
                or not issued < until <= issued + _MAX_RETENTION
                or type(name) is not str or _NAME.fullmatch(name) is None
                or not _sha(digest) or name in names or digest in digests
                or not _sha(entry["schema_sha256"])
                or entry["schema_sha256"] != schema_fingerprint
                or type(kid) is not str or _ID.fullmatch(kid) is None
                or type(key_id) is not str or key_id not in signer_keys
                or entry["previous_head"] != previous
                or not _sha(entry["mac"])):
            raise PermissionError("Recovery sequence, retention or source binding failed")
        if not hmac.compare_digest(entry["mac"], _mac(entry, signer_keys[key_id])):
            raise PermissionError("Recovery manifest signature mismatch")
        previous = _head(entry)
        previous_time = issued
        names.add(name)
        digests.add(digest)
        if now >= until:
            expired.append(name)
    if not hmac.compare_digest(previous, expected_head):
        raise PermissionError("Recovery head differs from external pin")
    return {"status": "disposable_recovery_chain_verified",
            "head": previous, "manifest_count": len(chain),
            "expired_archive_names": expired,
            "offsite_replica_verified": False,
            "independent_head_custody_verified": False,
            "key_escrow_verified": False,
            "retention_deletion_executed": False,
            "production_ready": False, "publishing_enabled": False}


def append_disposable_recovery_manifest(*, chain, expected_head, signer_keys,
                                        schema_fingerprint, now,
                                        receipt, signer_key_id,
                                        encryption_key_id, encryption_root_key,
                                        retain_until):
    """Build next signed metadata entry; caller must externally pin new head."""
    verify_disposable_recovery_chain(
        chain=chain, expected_head=expected_head, signer_keys=signer_keys,
        schema_fingerprint=schema_fingerprint, now=now)
    if len(chain) >= _MAX_MANIFESTS:
        raise PermissionError("Disposable manifest count exhausted")
    if (type(signer_key_id) is not str or signer_key_id not in signer_keys
            or type(encryption_key_id) is not str
            or _ID.fullmatch(encryption_key_id) is None
            or type(encryption_root_key) is not bytes
            or len(encryption_root_key) != 32
            or any(hmac.compare_digest(encryption_root_key, key)
                   for key in signer_keys.values())):
        raise ValueError("Distinct external encryption and signer keys required")
    if (type(receipt) is not dict
            or receipt.get("status") != "disposable_ciphertext_archived"
            or receipt.get("production_ready") is not False
            or receipt.get("offsite_copy_verified") is not False
            or type(receipt.get("archive_name")) is not str
            or _NAME.fullmatch(receipt["archive_name"]) is None
            or not _sha(receipt.get("ciphertext_sha256"))
            or type(receipt.get("bytes_on_disk")) is not int
            or not 0 < receipt["bytes_on_disk"] <= 8 * 1024 * 1024):
        raise ValueError("Actual disposable ciphertext archive receipt required")
    if (type(retain_until) is not int
            or not now < retain_until <= now + _MAX_RETENTION):
        raise ValueError("Finite synthetic retention horizon required")
    if any(entry["archive_name"] == receipt["archive_name"]
           or entry["ciphertext_sha256"] == receipt["ciphertext_sha256"]
           for entry in chain):
        raise PermissionError("Duplicate archived recovery point")
    entry = {"format": _FORMAT, "sequence": len(chain) + 1,
             "issued_at": now, "retain_until": retain_until,
             "archive_name": receipt["archive_name"],
             "ciphertext_sha256": receipt["ciphertext_sha256"],
             "schema_sha256": schema_fingerprint,
             "encryption_key_id": encryption_key_id,
             "signer_key_id": signer_key_id,
             "previous_head": expected_head}
    entry["mac"] = _mac(entry, signer_keys[signer_key_id])
    return tuple(chain) + (entry,), _head(entry)


def restore_disposable_recovery_point(*, chain, expected_head, signer_keys,
                                      encryption_keyring, directory,
                                      archive_name, schema_fingerprint, now):
    """Reopen actual local ciphertext only after full pin, signature and key checks."""
    verification = verify_disposable_recovery_chain(
        chain=chain, expected_head=expected_head, signer_keys=signer_keys,
        schema_fingerprint=schema_fingerprint, now=now)
    if type(archive_name) is not str or _NAME.fullmatch(archive_name) is None:
        raise ValueError("Exact approved recovery name required")
    selected = [entry for entry in chain if entry["archive_name"] == archive_name]
    if len(selected) != 1:
        raise KeyError("Recovery point not in independently verified chain")
    entry = selected[0]
    if now >= entry["retain_until"]:
        raise PermissionError("Recovery point past declared retention window")
    if type(encryption_keyring) is not dict:
        raise ValueError("Externally managed encryption keyring required")
    root = encryption_keyring.get(entry["encryption_key_id"])
    if (type(root) is not bytes or len(root) != 32
            or any(hmac.compare_digest(root, signer)
                   for signer in signer_keys.values())):
        raise PermissionError("Valid independent encryption key unavailable")
    # Physical ciphertext is reauthenticated with an independently pinned SHA
    # and the underlying AES-256-GCM envelope before plaintext is returned.
    plaintext = restore_disposable_ciphertext(
        directory=directory, name=archive_name, root_key=root,
        schema_fingerprint=schema_fingerprint, now=now,
        expected_ciphertext_sha256=entry["ciphertext_sha256"])
    if verification["production_ready"]:
        raise AssertionError("Disposable rehearsal must never authorize production")
    return plaintext
