"""Local-only signed ciphertext relocation after simulated source loss."""
import os
from pathlib import Path
import tempfile
import unittest

from offline_encrypted_backup import seal_disposable_backup
from bam_offline_durable_archive import store_disposable_ciphertext
from bam_offline_recovery_manifest import (
    append_disposable_recovery_manifest, restore_disposable_recovery_point)
from bam_offline_recovery_relocation import relocate_disposable_ciphertext

_SCHEMA = "c" * 64
_ROOT = b"e" * 32
_SIGNER = {"recovery-signer": b"s" * 32}
_EMPTY = "0" * 64
_PLAINTEXT = b"PRIVATE DISPOSABLE CI RECOVERY TEST ONLY"


class LocalRelocationTests(unittest.TestCase):
    def setUp(self):
        self.prior = os.environ.get("BAM_EPHEMERAL_PG_TEST")
        os.environ["BAM_EPHEMERAL_PG_TEST"] = "1"
        self.temp = tempfile.TemporaryDirectory()
        self.src = Path(self.temp.name) / "source"
        self.dst = Path(self.temp.name) / "replica"
        self.src.mkdir(mode=0o700)
        self.dst.mkdir(mode=0o700)
        self.name = "point_one.bamenc"
        blob = seal_disposable_backup(
            plaintext=_PLAINTEXT, root_key=_ROOT,
            schema_fingerprint=_SCHEMA, now=100)
        receipt = store_disposable_ciphertext(
            directory=str(self.src), name=self.name, envelope=blob,
            root_key=_ROOT, schema_fingerprint=_SCHEMA, now=101)
        self.chain, self.head = append_disposable_recovery_manifest(
            chain=(), expected_head=_EMPTY, signer_keys=_SIGNER,
            schema_fingerprint=_SCHEMA, now=102, receipt=receipt,
            signer_key_id="recovery-signer", encryption_key_id="root-1",
            encryption_root_key=_ROOT, retain_until=300)

    def tearDown(self):
        self.temp.cleanup()
        if self.prior is None:
            os.environ.pop("BAM_EPHEMERAL_PG_TEST", None)
        else:
            os.environ["BAM_EPHEMERAL_PG_TEST"] = self.prior

    def copy(self, **kwargs):
        options = dict(source_directory=str(self.src),
                       destination_directory=str(self.dst),
                       archive_name=self.name, chain=self.chain,
                       expected_head=self.head, signer_keys=_SIGNER,
                       schema_fingerprint=_SCHEMA, now=120)
        options.update(kwargs)
        return relocate_disposable_ciphertext(**options)

    def test_encrypted_replica_recovers_after_original_disappears(self):
        result = self.copy()
        self.assertEqual(result["signed_manifest_head"], self.head)
        self.assertFalse(result["offsite_replica_verified"])
        self.assertFalse(result["production_backup_ready"])
        self.assertFalse(result["local_replica_recovery_verified"])
        self.assertNotIn(_PLAINTEXT, (self.dst / self.name).read_bytes())
        (self.src / self.name).unlink()
        recovered = restore_disposable_recovery_point(
            chain=self.chain, expected_head=self.head, signer_keys=_SIGNER,
            encryption_keyring={"root-1": _ROOT},
            directory=str(self.dst), archive_name=self.name,
            schema_fingerprint=_SCHEMA, now=121)
        self.assertEqual(recovered, _PLAINTEXT)

    def test_rejects_replay_wrong_external_head_and_modified_source(self):
        with self.assertRaises(PermissionError):
            self.copy(expected_head="f" * 64)
        with self.assertRaises(PermissionError):
            self.copy(signer_keys={"recovery-signer": b"x" * 32})
        with self.assertRaises(PermissionError):
            self.copy(now=300)
        path = self.src / self.name
        modified = bytearray(path.read_bytes())
        modified[-1] ^= 1
        path.write_bytes(modified)
        with self.assertRaises(PermissionError):
            self.copy()
        self.assertFalse((self.dst / self.name).exists())

    def test_never_overwrites_or_reads_unsafe_inodes(self):
        self.copy()
        with self.assertRaises(FileExistsError):
            self.copy()
        (self.src / self.name).chmod(0o644)
        with self.assertRaises(PermissionError):
            self.copy()
        (self.src / self.name).chmod(0o600)
        with self.assertRaises(PermissionError):
            self.copy(destination_directory=str(self.src))
        with self.assertRaises(ValueError):
            self.copy(archive_name="../point_one.bamenc")

    def test_denies_untrusted_directory_and_inactive_mode(self):
        self.dst.chmod(0o755)
        with self.assertRaises(PermissionError):
            self.copy()
        self.dst.chmod(0o700)
        os.environ.pop("BAM_EPHEMERAL_PG_TEST")
        with self.assertRaises(PermissionError):
            self.copy()


if __name__ == "__main__":
    unittest.main()
