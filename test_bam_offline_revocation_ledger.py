"""Negative durable local revocation audit tests (no real media approval)."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from bam_offline_revocation_ledger import (
    load_disposable_revocation_audit, append_disposable_revocation_audit)

_KEY = b"separate-local-audit-rehearsal-key-1234567"
_ZERO = "0" * 64
_SCAN = {"kind": "scan", "signature": "a" * 64, "tenant_id": "tenant-one"}
_RIGHTS = {"kind": "rights", "signature": "b" * 64, "tenant_id": "tenant-one"}


class LocalAuditTests(unittest.TestCase):
    def setUp(self):
        self.saved = os.environ.get("BAM_EPHEMERAL_PG_TEST")
        os.environ["BAM_EPHEMERAL_PG_TEST"] = "1"
        self.tmp = tempfile.TemporaryDirectory()
        os.chmod(self.tmp.name, 0o700)

    def tearDown(self):
        self.tmp.cleanup()
        if self.saved is None:
            os.environ.pop("BAM_EPHEMERAL_PG_TEST", None)
        else:
            os.environ["BAM_EPHEMERAL_PG_TEST"] = self.saved

    def append(self, head, claim=_SCAN, kind="scan", reason="operator_hold"):
        return append_disposable_revocation_audit(
            directory=self.tmp.name, audit_key=_KEY, expected_head=head,
            claim=claim, kind=kind, reason=reason, now=150)

    def read(self, head, **kwargs):
        opts = dict(directory=self.tmp.name, audit_key=_KEY,
                    expected_head=head, now=160)
        opts.update(kwargs)
        return load_disposable_revocation_audit(**opts)

    def test_atomic_no_replace_pinned_replay_and_immutable_events(self):
        first = self.append(_ZERO)
        second = self.append(first["head"], _RIGHTS, "rights", "rights_withdrawn")
        chain, report = self.read(second["head"])
        self.assertEqual(len(chain), 2)
        self.assertEqual(report["event_count"], 2)
        self.assertTrue(first["event_written_locally"])
        self.assertFalse(first["external_latest_head_persisted"])
        self.assertFalse(first["production_ready"])
        self.assertFalse(report["production_audit_ready"])
        self.assertFalse(report["actual_scanning_performed"])
        self.assertEqual(sorted(p.name for p in Path(self.tmp.name).iterdir()),
                         ["rev-000001.json", "rev-000002.json"])
        self.assertEqual(list(Path(self.tmp.name).glob(".stage-*")), [])
        self.assertNotIn(str(_KEY), Path(self.tmp.name, "rev-000001.json")
                         .read_text())
        with self.assertRaises(PermissionError):
            self.append(first["head"], _RIGHTS, "rights")
        with self.assertRaises(PermissionError):
            self.append(second["head"])

    def test_tamper_missing_event_replay_and_wrong_pin_fail_closed(self):
        a = self.append(_ZERO)
        b = self.append(a["head"], _RIGHTS, "rights")
        first = Path(self.tmp.name, "rev-000001.json")
        second = Path(self.tmp.name, "rev-000002.json")
        with self.assertRaises(PermissionError):
            self.read(a["head"])
        with self.assertRaises(PermissionError):
            self.read(b["head"], audit_key=b"wrong-audit-worker-key-123456789123")
        content = first.read_text()
        first.write_text(content.replace("operator_hold", "scanner_recall"))
        with self.assertRaises(PermissionError):
            self.read(b["head"])
        first.write_text(content)
        second.unlink()
        with self.assertRaises(PermissionError):
            self.read(b["head"])

    def test_symlink_hardlink_and_permissions_are_rejected(self):
        a = self.append(_ZERO)
        target = Path(self.tmp.name, "rev-000001.json")
        target.chmod(0o644)
        with self.assertRaises(PermissionError):
            self.read(a["head"])
        target.chmod(0o600)
        link = Path(self.tmp.name, "rev-000002.json")
        os.link(target, link)
        with self.assertRaises(PermissionError):
            self.read(a["head"])
        link.unlink()
        target.unlink()
        target.symlink_to(Path(self.tmp.name, "rev-000009.json"))
        with self.assertRaises((PermissionError, OSError)):
            self.read(a["head"])

    def test_untrusted_path_extra_file_and_disabled_gate(self):
        with self.assertRaises(ValueError):
            self.read(_ZERO, directory="relative/path")
        Path(self.tmp.name, "unexpected.json").write_text("{}")
        with self.assertRaises(PermissionError):
            self.read(_ZERO)
        Path(self.tmp.name, "unexpected.json").unlink()
        self.assertEqual(self.read(_ZERO)[1]["event_count"], 0)
        os.chmod(self.tmp.name, 0o755)
        with self.assertRaises(PermissionError):
            self.read(_ZERO)
        os.chmod(self.tmp.name, 0o700)
        os.environ.pop("BAM_EPHEMERAL_PG_TEST")
        with self.assertRaises(PermissionError):
            self.read(_ZERO)

    def test_other_tenant_directory_cannot_replay_independent_pin(self):
        a = self.append(_ZERO)
        with tempfile.TemporaryDirectory() as other:
            os.chmod(other, 0o700)
            with self.assertRaises(PermissionError):
                self.read(a["head"], directory=other)


if __name__ == "__main__":
    unittest.main()
