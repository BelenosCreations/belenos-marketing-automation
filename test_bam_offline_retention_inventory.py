"""Read-only encrypted archive retention inventory; no deletion."""
import os
from pathlib import Path
import tempfile
import unittest

from offline_encrypted_backup import seal_disposable_backup
from bam_offline_durable_archive import store_disposable_ciphertext
from bam_offline_recovery_manifest import append_disposable_recovery_manifest
from bam_offline_retention_inventory import audit_disposable_retention_inventory

_SCHEMA = "d" * 64
_SIGNERS = {"review-signer": b"s" * 32}
_KEY = b"r" * 32
_ZERO = "0" * 64


class DisposableRetentionInventoryTests(unittest.TestCase):
    def setUp(self):
        self.previous = os.environ.get("BAM_EPHEMERAL_PG_TEST")
        os.environ["BAM_EPHEMERAL_PG_TEST"] = "1"
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name) / "archives"
        self.directory.mkdir(mode=0o700)
        self.chain = ()
        self.head = _ZERO
        self.add("first.bamenc", 100, 125)
        self.add("second.bamenc", 103, 300)

    def tearDown(self):
        self.temp.cleanup()
        if self.previous is None:
            os.environ.pop("BAM_EPHEMERAL_PG_TEST", None)
        else:
            os.environ["BAM_EPHEMERAL_PG_TEST"] = self.previous

    def add(self, name, when, retained_until):
        envelope = seal_disposable_backup(
            plaintext=("CI fixture " + name).encode("ascii"),
            root_key=_KEY, schema_fingerprint=_SCHEMA, now=when)
        receipt = store_disposable_ciphertext(
            directory=str(self.directory), name=name, envelope=envelope,
            root_key=_KEY, schema_fingerprint=_SCHEMA, now=when + 1)
        self.chain, self.head = append_disposable_recovery_manifest(
            chain=self.chain, expected_head=self.head,
            signer_keys=_SIGNERS, schema_fingerprint=_SCHEMA,
            now=when + 2, receipt=receipt, signer_key_id="review-signer",
            encryption_key_id="key-one", encryption_root_key=_KEY,
            retain_until=retained_until)

    def audit(self, **changes):
        params = dict(directory=str(self.directory), chain=self.chain,
                      expected_head=self.head, signer_keys=_SIGNERS,
                      schema_fingerprint=_SCHEMA, now=120)
        params.update(changes)
        return audit_disposable_retention_inventory(**params)

    def test_detects_expiration_without_deleting_or_decrypting(self):
        before = {p.name: p.read_bytes() for p in self.directory.iterdir()}
        report = self.audit()
        self.assertEqual(report["verified_archive_count"], 2)
        self.assertEqual(report["retained_archive_names"],
                         ["first.bamenc", "second.bamenc"])
        self.assertEqual(report["expired_archive_names_for_manual_review"], [])
        expired = self.audit(now=125)
        self.assertEqual(expired["expired_archive_names_for_manual_review"],
                         ["first.bamenc"])
        self.assertEqual(expired["retained_archive_names"], ["second.bamenc"])
        self.assertFalse(expired["files_deleted"])
        self.assertFalse(expired["retention_policy_enforced_by_deletion"])
        self.assertFalse(expired["restore_rehearsed_by_this_audit"])
        self.assertFalse(expired["offsite_replica_verified"])
        self.assertFalse(expired["customer_backup_proven"])
        self.assertEqual(before, {p.name: p.read_bytes()
                                  for p in self.directory.iterdir()})

    def test_missing_unknown_and_truncated_ciphertext_fail_closed(self):
        (self.directory / "unexpected.bamenc").write_bytes(b"fake")
        with self.assertRaises(PermissionError):
            self.audit()
        (self.directory / "unexpected.bamenc").unlink()
        source = self.directory / "first.bamenc"
        blob = source.read_bytes()
        source.write_bytes(blob[:-1])
        with self.assertRaises(PermissionError):
            self.audit()
        source.write_bytes(blob)
        source.unlink()
        with self.assertRaises(PermissionError):
            self.audit()

    def test_permission_link_and_symlink_attacks_fail_closed(self):
        archive = self.directory / "first.bamenc"
        archive.chmod(0o644)
        with self.assertRaises(PermissionError):
            self.audit()
        archive.chmod(0o600)
        hardlink = self.directory / "linked"
        os.link(archive, hardlink)
        with self.assertRaises(PermissionError):
            self.audit()
        hardlink.unlink()
        data = archive.read_bytes()
        archive.unlink()
        archive.symlink_to(self.directory / "second.bamenc")
        with self.assertRaises((PermissionError, OSError)):
            self.audit()
        archive.unlink()
        archive.write_bytes(data)
        archive.chmod(0o600)
        self.directory.chmod(0o755)
        with self.assertRaises(PermissionError):
            self.audit()

    def test_wrong_signature_head_and_disabled_mode_do_not_audit(self):
        with self.assertRaises(PermissionError):
            self.audit(expected_head="f" * 64)
        with self.assertRaises(PermissionError):
            self.audit(signer_keys={"review-signer": b"q" * 32})
        os.environ.pop("BAM_EPHEMERAL_PG_TEST")
        with self.assertRaises(PermissionError):
            self.audit()


if __name__ == "__main__":
    unittest.main()
