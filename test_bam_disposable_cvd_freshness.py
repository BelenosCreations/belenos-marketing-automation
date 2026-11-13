"""Adversarial synthetic CVD header parsing, no genuine scanner or signatures."""
import datetime
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bam_disposable_cvd_freshness import (
    inspect_disposable_daily_cvd_header,
)


class DisposableCVDFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.old = os.environ.get("BAM_EPHEMERAL_PG_TEST")
        os.environ["BAM_EPHEMERAL_PG_TEST"] = "1"
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "daily.cvd"
        self.now = int(datetime.datetime(
            2026, 11, 13, tzinfo=datetime.timezone.utc).timestamp())
        self.write_fixture(self.now - 3600)

    def tearDown(self):
        self.tmp.cleanup()
        if self.old is None:
            os.environ.pop("BAM_EPHEMERAL_PG_TEST", None)
        else:
            os.environ["BAM_EPHEMERAL_PG_TEST"] = self.old

    def write_fixture(self, issued, *, human=None, version="101",
                      signature="A" * 48, preface="ClamAV-VDB",
                      timestamp=None):
        text_time = (datetime.datetime.fromtimestamp(
            issued, datetime.timezone.utc).strftime("%d %b %Y %H:%M %z")
            if human is None else human)
        header = ":".join((
            preface, text_time, version, "12345", "90",
            "a" * 32, signature, "ci_fixture", str(
                issued if timestamp is None else timestamp)))
        data = header.encode("ascii").ljust(512, b" ") + b"synthetic-not-signatures"
        self.path.write_bytes(data)
        self.path.chmod(0o600)
        return hashlib.sha256(data).hexdigest()

    def inspect(self, **changes):
        args = dict(database_path=str(self.path),
                    independently_pinned_sha256=hashlib.sha256(
                        self.path.read_bytes()).hexdigest(),
                    now=self.now, maximum_age_seconds=48 * 3600)
        args.update(changes)
        return inspect_disposable_daily_cvd_header(**args)

    def test_synthetic_digest_and_header_claims_do_not_authorize_media(self):
        report = self.inspect()
        self.assertEqual(report["claimed_header_age_seconds"], 3600)
        self.assertEqual(report["claimed_database_version"], 101)
        self.assertTrue(report["whole_file_matches_caller_pin"])
        for flag in (
            "signature_origin_authenticated",
            "embedded_digital_signature_verified",
            "actual_clamav_engine_invoked",
            "isolated_scanner_worker_proven",
            "complete_scanner_database_set_verified",
            "scan_evidence_issued", "media_rights_approved",
            "attachment_state_changed", "production_ready",
            "publishing_enabled",
        ):
            self.assertFalse(report[flag], flag)
        self.assertNotIn(str(self.path), str(report))

    def test_stale_future_disagreeing_or_forged_header_rejected(self):
        samples = (
            {"issued": self.now - 3 * 86400},
            {"issued": self.now + 1},
            {"issued": self.now - 3600, "timestamp": self.now - 7200},
            {"issued": self.now - 3600, "human": "not-a-date"},
            {"issued": self.now - 3600, "version": "false"},
            {"issued": self.now - 3600, "version": "0"},
            {"issued": self.now - 3600, "signature": "BAD-sig"},
            {"issued": self.now - 3600, "preface": "Forged-VDB"},
        )
        for sample in samples:
            with self.subTest(sample=sample):
                params = dict(sample)
                issued = params.pop("issued")
                self.write_fixture(issued, **params)
                with self.assertRaises(PermissionError):
                    self.inspect()

    def test_mutated_bytes_bad_pins_and_file_links_rejected(self):
        pin = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.path.write_bytes(self.path.read_bytes() + b"unexpected")
        with self.assertRaises(PermissionError):
            self.inspect(independently_pinned_sha256=pin)
        self.write_fixture(self.now - 3600)
        alias = Path(self.tmp.name) / "linked.cvd"
        os.link(self.path, alias)
        with self.assertRaises(PermissionError):
            self.inspect()
        alias.unlink()
        target = Path(self.tmp.name) / "copy.cvd"
        self.path.rename(target)
        self.path.symlink_to(target)
        with self.assertRaises((PermissionError, OSError)):
            self.inspect()
        self.path.unlink()
        target.rename(self.path)
        self.path.chmod(0o666)
        with self.assertRaises(PermissionError):
            self.inspect()

    def test_no_subprocess_no_network_and_disabled_mode(self):
        with patch("bam_disposable_cvd_freshness.os.open") as forbidden:
            os.environ.pop("BAM_EPHEMERAL_PG_TEST")
            with self.assertRaises(PermissionError):
                self.inspect()
            forbidden.assert_not_called()
        os.environ["BAM_EPHEMERAL_PG_TEST"] = "1"
        for update in (
            {"maximum_age_seconds": 0},
            {"maximum_age_seconds": True},
            {"now": False},
            {"now": self.now + 2 ** 64},
            {"independently_pinned_sha256": "wrong"},
            {"database_path": "../daily.cvd"},
            {"database_path": str(Path(self.tmp.name) / "main.cvd")},
        ):
            with self.subTest(update=update):
                with self.assertRaises(ValueError):
                    self.inspect(**update)


if __name__ == "__main__":
    unittest.main()
