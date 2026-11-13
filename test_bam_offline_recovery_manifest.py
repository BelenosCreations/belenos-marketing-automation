"""Encrypted recovery chain, signer/encryption rotation and negative tests."""
import copy
import os
import pathlib
import tempfile
import unittest

from offline_encrypted_backup import seal_disposable_backup
from bam_offline_durable_archive import store_disposable_ciphertext
from bam_offline_recovery_manifest import (
    append_disposable_recovery_manifest, verify_disposable_recovery_chain,
    restore_disposable_recovery_point)

_SCHEMA = "a" * 64
_ROOT_1, _ROOT_2 = b"r" * 32, b"t" * 32
_SIGNERS = {"signer-1": b"s" * 32, "signer-2": b"u" * 32}
_Z = "0" * 64


class RecoveryManifestTests(unittest.TestCase):
    def setUp(self):
        self.previous = os.environ.get("BAM_EPHEMERAL_PG_TEST")
        os.environ["BAM_EPHEMERAL_PG_TEST"] = "1"
        self.tmp = tempfile.TemporaryDirectory()
        os.chmod(self.tmp.name, 0o700)

    def tearDown(self):
        self.tmp.cleanup()
        if self.previous is None:
            os.environ.pop("BAM_EPHEMERAL_PG_TEST", None)
        else:
            os.environ["BAM_EPHEMERAL_PG_TEST"] = self.previous

    def archive(self, name, plaintext, root, at):
        envelope = seal_disposable_backup(
            plaintext=plaintext, root_key=root,
            schema_fingerprint=_SCHEMA, now=at)
        return store_disposable_ciphertext(
            directory=self.tmp.name, name=name, envelope=envelope,
            root_key=root, schema_fingerprint=_SCHEMA, now=at)

    def build(self):
        a = self.archive("backup_one.bamenc", b"CI SYNTHETIC ONE",
                         _ROOT_1, 100)
        chain, head = append_disposable_recovery_manifest(
            chain=(), expected_head=_Z, signer_keys=_SIGNERS,
            schema_fingerprint=_SCHEMA, now=101, receipt=a,
            signer_key_id="signer-1", encryption_key_id="key-1",
            encryption_root_key=_ROOT_1, retain_until=300)
        b = self.archive("backup_two.bamenc", b"CI SYNTHETIC TWO",
                         _ROOT_2, 105)
        chain, head = append_disposable_recovery_manifest(
            chain=chain, expected_head=head, signer_keys=_SIGNERS,
            schema_fingerprint=_SCHEMA, now=110, receipt=b,
            signer_key_id="signer-2", encryption_key_id="key-2",
            encryption_root_key=_ROOT_2, retain_until=200)
        return chain, head

    def verified(self, chain, head, **extra):
        args = dict(chain=chain, expected_head=head, signer_keys=_SIGNERS,
                    schema_fingerprint=_SCHEMA, now=120)
        args.update(extra)
        return verify_disposable_recovery_chain(**args)

    def restore(self, chain, head, name, **extra):
        args = dict(chain=chain, expected_head=head, signer_keys=_SIGNERS,
                    encryption_keyring={"key-1": _ROOT_1, "key-2": _ROOT_2},
                    directory=self.tmp.name, archive_name=name,
                    schema_fingerprint=_SCHEMA, now=120)
        args.update(extra)
        return restore_disposable_recovery_point(**args)

    def test_ciphertext_manifest_and_independent_key_rotation(self):
        chain, head = self.build()
        result = self.verified(chain, head)
        self.assertEqual(result["manifest_count"], 2)
        self.assertEqual(result["head"], head)
        self.assertFalse(result["production_ready"])
        self.assertFalse(result["offsite_replica_verified"])
        self.assertFalse(result["independent_head_custody_verified"])
        self.assertFalse(result["retention_deletion_executed"])
        self.assertEqual(self.restore(chain, head, "backup_one.bamenc"),
                         b"CI SYNTHETIC ONE")
        self.assertEqual(self.restore(chain, head, "backup_two.bamenc"),
                         b"CI SYNTHETIC TWO")
        self.assertNotIn(str(_ROOT_1), str(chain))
        self.assertNotIn(str(_SIGNERS["signer-1"]), str(chain))

    def test_tamper_replay_truncation_and_external_pin_denied(self):
        chain, head = self.build()
        with self.assertRaises(PermissionError):
            self.verified(chain[:1], head)
        with self.assertRaises(PermissionError):
            self.verified(chain[::-1], head)
        with self.assertRaises(PermissionError):
            self.verified(chain, "f" * 64)
        tampered = copy.deepcopy(chain)
        tampered[0]["archive_name"] = "bad.bamenc"
        with self.assertRaises(PermissionError):
            self.verified(tampered, head)
        with self.assertRaises(PermissionError):
            self.verified(chain + chain[1:], head)
        with self.assertRaises(PermissionError):
            self.verified(chain, head,
                          signer_keys={"signer-1": b"q" * 32,
                                       "signer-2": b"u" * 32})

    def test_wrong_encryption_keys_retention_and_byte_changes_denied(self):
        chain, head = self.build()
        with self.assertRaises(PermissionError):
            self.restore(chain, head, "backup_one.bamenc",
                         encryption_keyring={"key-1": _ROOT_2,
                                             "key-2": _ROOT_2})
        with self.assertRaises(PermissionError):
            self.restore(chain, head, "backup_two.bamenc", now=200)
        self.assertEqual(self.verified(chain, head, now=201)
                         ["expired_archive_names"], ["backup_two.bamenc"])
        with self.assertRaises(KeyError):
            self.restore(chain, head, "unknown.bamenc")
        path = pathlib.Path(self.tmp.name) / "backup_one.bamenc"
        mutated = bytearray(path.read_bytes())
        mutated[-1] ^= 1
        path.write_bytes(mutated)
        with self.assertRaises(PermissionError):
            self.restore(chain, head, "backup_one.bamenc")

    def test_bad_receipt_key_reuse_and_disabled_path(self):
        receipt = self.archive("backup_one.bamenc", b"CI TEST", _ROOT_1, 100)
        args = dict(chain=(), expected_head=_Z, signer_keys=_SIGNERS,
                    schema_fingerprint=_SCHEMA, now=101, receipt=receipt,
                    signer_key_id="signer-1", encryption_key_id="key-1",
                    encryption_root_key=_ROOT_1, retain_until=300)
        for patch in ({"encryption_root_key": _SIGNERS["signer-1"]},
                      {"signer_key_id": "missing"},
                      {"retain_until": 101},
                      {"receipt": {**receipt, "production_ready": True}}):
            with self.subTest(patch=str(patch)), self.assertRaises(ValueError):
                append_disposable_recovery_manifest(**{**args, **patch})
        with self.assertRaises(ValueError):
            self.verified((), _Z,
                          signer_keys={"signer-1": b"s" * 32,
                                       "signer-2": b"s" * 32})
        os.environ.pop("BAM_EPHEMERAL_PG_TEST")
        with self.assertRaises(PermissionError):
            self.verified((), _Z)


if __name__ == "__main__":
    unittest.main()
