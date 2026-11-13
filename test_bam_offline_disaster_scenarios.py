"""CI-only hostile negative scenarios against signed synthetic receipts."""
import copy
import os
from pathlib import Path
import tempfile
import unittest

from offline_encrypted_backup import seal_disposable_backup
from bam_offline_durable_archive import store_disposable_ciphertext
from bam_offline_recovery_manifest import append_disposable_recovery_manifest
from bam_offline_disaster_scenarios import plan_disposable_recovery_incident

_SCHEMA = "b" * 64
_ROOTS = {"root-a": b"x" * 32, "root-b": b"z" * 32}
_SIGNERS = {"sign-a": b"s" * 32, "sign-b": b"t" * 32}
_GENESIS = "0" * 64


class OfflineDisasterScenarioTests(unittest.TestCase):
    def setUp(self):
        self.old = os.environ.get("BAM_EPHEMERAL_PG_TEST")
        os.environ["BAM_EPHEMERAL_PG_TEST"] = "1"
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self.tmp.name) / "archives"
        self.directory.mkdir(mode=0o700)
        self.chain, self.head = (), _GENESIS
        self.add("early.bamenc", now=100, until=260,
                 signer_id="sign-a", encryption_id="root-a")
        self.add("recent.bamenc", now=110, until=170,
                 signer_id="sign-b", encryption_id="root-b")

    def tearDown(self):
        self.tmp.cleanup()
        if self.old is None:
            os.environ.pop("BAM_EPHEMERAL_PG_TEST", None)
        else:
            os.environ["BAM_EPHEMERAL_PG_TEST"] = self.old

    def add(self, name, *, now, until, signer_id, encryption_id):
        root = _ROOTS[encryption_id]
        envelope = seal_disposable_backup(
            plaintext=("CI-only " + name).encode("ascii"),
            root_key=root, schema_fingerprint=_SCHEMA, now=now)
        receipt = store_disposable_ciphertext(
            directory=str(self.directory), name=name, envelope=envelope,
            root_key=root, schema_fingerprint=_SCHEMA, now=now + 1)
        self.chain, self.head = append_disposable_recovery_manifest(
            chain=self.chain, expected_head=self.head,
            signer_keys=_SIGNERS, schema_fingerprint=_SCHEMA,
            now=now + 2, receipt=receipt, signer_key_id=signer_id,
            encryption_key_id=encryption_id, encryption_root_key=root,
            retain_until=until)

    def plan(self, **updates):
        args = dict(chain=self.chain, expected_head=self.head,
                    signer_keys=_SIGNERS, schema_fingerprint=_SCHEMA,
                    now=120, incident_at=115, max_manifest_age_seconds=20,
                    claimed_available_encryption_key_ids=["root-a", "root-b"],
                    scenario="source_directory_loss")
        args.update(updates)
        return plan_disposable_recovery_incident(**args)

    def test_newest_manifest_candidate_is_never_proven_backup(self):
        result = self.plan()
        self.assertEqual(result["signed_manifest_count"], 2)
        self.assertEqual(result["candidate_count_based_on_unverified_key_claims"], 2)
        self.assertEqual(result["potential_manifest_archive_name_unverified"],
                         "recent.bamenc")
        self.assertEqual(result["potential_manifest_age_at_incident_seconds"], 3)
        for key in ("archive_existence_checked", "ciphertext_integrity_checked",
                    "offsite_replica_verified", "decrypt_attempted",
                    "restore_executed", "customer_backup_proven"):
            self.assertFalse(result[key])
        self.assertTrue(result["manifest_age_is_not_measured_rpo"])

    def test_missing_keys_age_and_expiration_change_candidates(self):
        no_recent_key = self.plan(
            claimed_available_encryption_key_ids=["root-a"])
        self.assertEqual(no_recent_key["potential_manifest_archive_name_unverified"],
                         "early.bamenc")
        self.assertEqual(no_recent_key["potential_manifest_age_at_incident_seconds"], 13)
        too_old = self.plan(
            max_manifest_age_seconds=2)
        self.assertIsNone(too_old["potential_manifest_archive_name_unverified"])
        self.assertIn("no_unexpired_signed_point_with_claimed_key_in_age_window",
                      too_old["blockers"])
        after_expiration = self.plan(now=180)
        self.assertEqual(
            after_expiration["potential_manifest_archive_name_unverified"],
            "early.bamenc")
        no_keys = self.plan(claimed_available_encryption_key_ids=[])
        self.assertEqual(no_keys["candidate_count_based_on_unverified_key_claims"], 0)

    def test_whole_host_loss_never_claims_offsite(self):
        report = self.plan(scenario="whole_host_loss")
        self.assertIn("offsite_replica_and_independent_failure_domain_not_proven",
                      report["blockers"])
        self.assertFalse(report["independent_failure_domain_verified"])
        self.assertFalse(report["production_backup_ready"])
        # Deliberately remove local synthetic bytes: planning cannot detect it,
        # and must therefore never claim physical restore readiness.
        for file in self.directory.iterdir():
            file.unlink()
        self.assertEqual(report, self.plan(scenario="whole_host_loss"))

    def test_tamper_replay_pin_and_signer_fail_closed(self):
        with self.assertRaises(PermissionError):
            self.plan(expected_head="f" * 64)
        with self.assertRaises(PermissionError):
            self.plan(signer_keys={"sign-a": b"k" * 32,
                                   "sign-b": b"t" * 32})
        tampered = list(copy.deepcopy(self.chain))
        tampered[0]["archive_name"] = "changed.bamenc"
        with self.assertRaises(PermissionError):
            self.plan(chain=tampered)
        with self.assertRaises(PermissionError):
            self.plan(chain=list(reversed(self.chain)))

    def test_invalid_inputs_and_inactive_mode_fail_closed(self):
        for data in (
            {"scenario": "real_customer_restore"},
            {"incident_at": 130},
            {"incident_at": True},
            {"max_manifest_age_seconds": -1},
            {"max_manifest_age_seconds": True},
            {"claimed_available_encryption_key_ids": ["root-a", "root-a"]},
            {"claimed_available_encryption_key_ids": ["../../bad"]},
            {"claimed_available_encryption_key_ids": "root-a"},
        ):
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.plan(**data)
        os.environ.pop("BAM_EPHEMERAL_PG_TEST")
        with self.assertRaises(PermissionError):
            self.plan()


if __name__ == "__main__":
    unittest.main()
