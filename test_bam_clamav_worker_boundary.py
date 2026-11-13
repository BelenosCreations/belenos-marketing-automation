"""ClamAV invocation boundary negative cases; subprocess is always MOCKED.

A fake version output proves only CLI plumbing, NEVER authentic scan execution.
"""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from bam_clamav_worker_boundary import scan_disposable_clamav_candidate

def digest(data):
    return hashlib.sha256(data).hexdigest()

class ClamAVBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.prev = os.environ.get("BAM_EPHEMERAL_PG_TEST")
        os.environ["BAM_EPHEMERAL_PG_TEST"] = "1"
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.exe = root / "clamscan"
        self.db = root / "daily.cvd"
        self.media = root / "staged"
        self.media.mkdir(mode=0o700)
        self.name = "a" * 32 + ".pending"
        self.staged = self.media / self.name
        self.exe.write_bytes(b"synthetic-placeholder-executable")
        self.exe.chmod(0o700)
        self.db.write_bytes(b"synthetic-placeholder-signatures")
        self.db.chmod(0o600)
        self.staged.write_bytes(b"synthetic-pending-media")
        self.staged.chmod(0o600)
        self.args = dict(
            executable_path=str(self.exe), database_path=str(self.db),
            staged_directory=str(self.media), staged_name=self.name,
            executable_sha256=digest(self.exe.read_bytes()),
            database_sha256=digest(self.db.read_bytes()),
            staged_sha256=digest(self.staged.read_bytes()))

    def tearDown(self):
        self.tmp.cleanup()
        if self.prev is None:
            os.environ.pop("BAM_EPHEMERAL_PG_TEST", None)
        else:
            os.environ["BAM_EPHEMERAL_PG_TEST"] = self.prev

    def call(self, **overrides):
        return scan_disposable_clamav_candidate(**{**self.args, **overrides})

    @staticmethod
    def simulated(cmd, **kwargs):
        assert kwargs["check"] is False
        assert kwargs["close_fds"] is True
        assert kwargs["cwd"] == "/"
        assert "HTTP_PROXY" not in kwargs["env"]
        assert "--version" in cmd or "--no-summary" in cmd
        if "--version" in cmd:
            return subprocess.CompletedProcess(cmd, 0, b"ClamAV 1.4.2/999/example\n", b"")
        return subprocess.CompletedProcess(cmd, 0, b"synthetic: OK\n", b"")

    def test_mocked_cli_plumbing_never_proves_engine_or_approves_media(self):
        with patch("bam_clamav_worker_boundary.subprocess.run",
                   side_effect=self.simulated) as runner:
            result = self.call()
        self.assertEqual(runner.call_count, 2)
        self.assertEqual(result["candidate_verdict"], "clean")
        self.assertFalse(result["genuine_engine_execution_proven_in_ci"])
        self.assertFalse(result["trusted_worker_isolation_proven"])
        self.assertFalse(result["origin_of_external_pins_verified"])
        self.assertFalse(result["signed_scan_evidence_issued"])
        self.assertFalse(result["media_approval_allowed"])
        self.assertFalse(result["attachment_status_changed"])
        self.assertNotIn(str(self.staged), str(result))

    def test_mocked_detections_or_errors_never_become_clean(self):
        def infected(cmd, **kw):
            if "--version" in cmd:
                return subprocess.CompletedProcess(cmd, 0, b"ClamAV 1.4.2\n", b"")
            return subprocess.CompletedProcess(cmd, 1, b"simulated: FOUND", b"")
        with patch("bam_clamav_worker_boundary.subprocess.run", side_effect=infected):
            self.assertEqual(self.call()["candidate_verdict"], "infected")
        def error(cmd, **kw):
            if "--version" in cmd:
                return subprocess.CompletedProcess(cmd, 0, b"ClamAV 1.4.2\n", b"")
            return subprocess.CompletedProcess(cmd, 2, b"", b"simulated scan error")
        with patch("bam_clamav_worker_boundary.subprocess.run", side_effect=error):
            with self.assertRaises(PermissionError):
                self.call()
        with patch("bam_clamav_worker_boundary.subprocess.run",
                   side_effect=subprocess.TimeoutExpired(["clamscan"], 1)):
            with self.assertRaises(PermissionError):
                self.call()

    def test_wrong_hash_invalid_file_type_permission_and_links_fail(self):
        for field in ("executable_sha256", "database_sha256", "staged_sha256"):
            with self.subTest(field=field), self.assertRaises(PermissionError):
                self.call(**{field: "f" * 64})
        self.exe.chmod(0o722)
        with self.assertRaises(PermissionError):
            self.call()
        self.exe.chmod(0o700)
        self.db.chmod(0o666)
        with self.assertRaises(PermissionError):
            self.call()
        self.db.chmod(0o600)
        linked = Path(self.tmp.name) / "linked.cvd"
        os.link(self.db, linked)
        with self.assertRaises(PermissionError):
            self.call()
        linked.unlink()
        self.staged.chmod(0o644)
        with self.assertRaises(PermissionError):
            self.call()
        self.staged.chmod(0o600)

    def test_mutation_during_mock_scan_detected_and_never_approved(self):
        def mutate(cmd, **kw):
            if "--version" in cmd:
                return subprocess.CompletedProcess(cmd, 0, b"ClamAV 1.4.2\n", b"")
            self.staged.write_bytes(b"modified")
            return subprocess.CompletedProcess(cmd, 0, b"fake: OK", b"")
        with patch("bam_clamav_worker_boundary.subprocess.run", side_effect=mutate):
            with self.assertRaises(PermissionError):
                self.call()

    def test_rejects_untrusted_names_missing_engine_and_disabled_execution(self):
        for kw in ({"staged_name": "../a.pending"},
                   {"executable_path": str(self.db)},
                   {"database_path": str(self.exe)},
                   {"executable_path": "clamscan"}):
            with self.subTest(kw=kw), self.assertRaises((ValueError, PermissionError)):
                self.call(**kw)
        os.environ.pop("BAM_EPHEMERAL_PG_TEST")
        with self.assertRaises(PermissionError):
            self.call()


if __name__ == "__main__":
    unittest.main()
