import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from neon_ci_wsgi_write_boundary_review import (
    _REVIEWED_SOURCE,
    inspect_ci_wsgi_write_boundaries,
)


_ROOT = Path(__file__).resolve().parent


def _delegate(report, attribute, method):
    return next(
        call
        for handler in report["handler_candidates"]
        if handler["gateway_attribute"] == attribute
        for call in handler["syntactic_delegate_calls"]
        if call["candidate_method"] == method
    )


class WSGIWriteBoundaryReviewTests(unittest.TestCase):
    def setUp(self):
        gate = patch.dict(os.environ, {"BAM_EPHEMERAL_PG_TEST": "1"})
        gate.start()
        self.addCleanup(gate.stop)

    def _fixture(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        for name in _REVIEWED_SOURCE:
            shutil.copyfile(_ROOT / name, root / name)
        return root

    def test_sql_contexts_and_filesystem_order(self):
        report = inspect_ci_wsgi_write_boundaries()
        self.assertEqual(report["drifted_reviewed_source"], [])
        for attribute, method, file, boundary, mutation in (
            ("content_write_wsgi", "create_held_draft", "content_requests.py", 64, 65),
            ("content_write_wsgi", "update_draft_hold", "content_requests.py", 177, 178),
            ("content_revise_wsgi", "revise_held_draft", "content_requests.py", 199, 200),
            ("content_priority_wsgi", "update_held_priority", "content_requests.py", 115, 116),
            ("upload_preflight_wsgi", "begin_content_upload_preflight", "content_attachments.py", 39, 40),
        ):
            with self.subTest(method=method):
                call = _delegate(report, attribute, method)
                self.assertEqual(call["boundary_status"], "reviewed_source_write_path")
                [site] = call["mutation_sites"]
                self.assertEqual((site["module"], site["sqlite_context_line"], site["line"]),
                                 (file, boundary, mutation))
                self.assertIn("with self.db:", (_ROOT / file).read_text().splitlines()[boundary - 1])
        receipt = _delegate(report, "pending_media_wsgi", "receive")
        self.assertEqual([site["kind"] for site in receipt["mutation_sites"]],
                         ["file_create", "file_write", "file_fsync", "file_unlink_on_error"])
        self.assertTrue(all(site["sqlite_context_line"] is None
                            for site in receipt["mutation_sites"]))
        discard = _delegate(report, "pending_discard_wsgi", "discard")
        unlink, delete = discard["mutation_sites"]
        self.assertEqual((unlink["kind"], delete["kind"]), ("file_unlink", "sql_delete"))
        self.assertLess(unlink["line"], delete["sqlite_context_line"])
        self.assertLess(delete["sqlite_context_line"], delete["line"])

    def test_unreviewed_and_indirect_calls_remain_visible(self):
        report = inspect_ci_wsgi_write_boundaries()
        self.assertFalse(report["deployed_writer_inventory_complete"])
        self.assertFalse(report["transaction_generation_fencing_proven"])
        self.assertEqual(_delegate(report, "auth_wsgi", "password_login")["boundary_status"],
                         "unreviewed_delegate")
        self.assertEqual(_delegate(report, "pending_status_wsgi", "statuses")["boundary_status"],
                         "no_direct_mutation_in_reviewed_body")
        alias_handler = next(h for h in report["handler_candidates"]
                             if h["gateway_attribute"] == "local_draft_wsgi")
        self.assertEqual(alias_handler["boundary_scope"], "unresolved_no_delegate")

    def test_missing_and_dynamic_sources_invalidate_reviewed_paths(self):
        root = self._fixture()
        baseline = inspect_ci_wsgi_write_boundaries(source_root=root)
        self.assertEqual(baseline, inspect_ci_wsgi_write_boundaries(source_root=root))
        service = root / "content_request_service.py"
        text = service.read_text()
        service.write_text(text.replace("self.requests.create(", "getattr(self.requests, 'create')("))
        (root / "content_byte_inspector.py").unlink()
        report = inspect_ci_wsgi_write_boundaries(source_root=root)
        self.assertEqual(report["drifted_reviewed_source"],
                         ["content_byte_inspector.py", "content_request_service.py"])
        self.assertNotEqual(report["review_sha256"], baseline["review_sha256"])
        call = _delegate(report, "content_write_wsgi", "create_held_draft")
        self.assertEqual(call["boundary_status"], "reviewed_source_drift")
        self.assertEqual(call["mutation_sites"], [])
        self.assertIsNone(report["observed_source_sha256"]["content_byte_inspector.py"])

    def test_unrelated_handler_with_same_method_is_not_a_reviewed_path(self):
        root = self._fixture()
        gateway = root / "bam_offline_gateway.py"
        gateway.write_text(gateway.read_text().replace("self.content_write_wsgi",
                                                        "self.other_wsgi"))
        report = inspect_ci_wsgi_write_boundaries(source_root=root)
        call = _delegate(report, "other_wsgi", "create_held_draft")
        self.assertEqual(call["boundary_status"], "unreviewed_delegate")
        self.assertEqual(call["mutation_sites"], [])

    def test_rejects_linked_sources_and_requires_ci_gate(self):
        root = self._fixture()
        source = root / "content_attachments.py"
        source.unlink()
        source.symlink_to(_ROOT / source.name)
        with self.assertRaises(PermissionError):
            inspect_ci_wsgi_write_boundaries(source_root=root)
        with patch.dict(os.environ, {"BAM_EPHEMERAL_PG_TEST": "0"}):
            with self.assertRaises(PermissionError):
                inspect_ci_wsgi_write_boundaries()


if __name__ == "__main__":
    unittest.main()
