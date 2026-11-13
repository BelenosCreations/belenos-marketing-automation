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
        self.assertEqual(_delegate(report, "read_wsgi", "get_dashboard_view")["boundary_status"],
                         "unreviewed_delegate")
        self.assertEqual(_delegate(report, "pending_status_wsgi", "statuses")["boundary_status"],
                         "no_direct_mutation_in_reviewed_body")
        alias_handler = next(h for h in report["handler_candidates"]
                             if h["gateway_attribute"] == "local_draft_wsgi")
        self.assertEqual(alias_handler["boundary_scope"], "unresolved_no_delegate")

    def test_pinned_local_draft_aliases_map_to_the_same_insert(self):
        report = inspect_ci_wsgi_write_boundaries()
        for attribute, method in (
            ("local_draft_wsgi", "create_local_product_draft"),
            ("local_service_wsgi", "create_local_service_draft"),
        ):
            handler = next(h for h in report["handler_candidates"]
                           if h["gateway_attribute"] == attribute)
            self.assertEqual(handler["syntactic_delegate_calls"], [])
            [call] = handler["manually_reviewed_alias_calls"]
            self.assertEqual(call["candidate_method"], method)
            self.assertEqual(call["source_evidence"], "manual_pinned_alias")
            self.assertEqual(call["boundary_status"], "reviewed_source_write_path")
            [site] = call["mutation_sites"]
            self.assertEqual(site, {
                "kind": "sql_insert", "module": "ai_content_drafts.py",
                "line": 50, "sqlite_context_line": 49, "sqlite_explicit_commit_line": None,
            })

    def test_auth_and_membership_keep_distinct_commits_and_dynamic_dependencies(self):
        report = inspect_ci_wsgi_write_boundaries()
        password = _delegate(report, "auth_wsgi", "password_login")
        issue, success, failure = password["mutation_sites"]
        self.assertEqual((issue["line"], issue["sqlite_explicit_commit_line"]), (50, 54))
        self.assertIsNone(issue["sqlite_context_line"])
        self.assertEqual([site["sqlite_context_line"] for site in (success, failure)],
                         [67, 51])
        google = _delegate(report, "auth_wsgi", "google_login")
        self.assertEqual(google["unresolved_dependencies"],
                         ["AuthLoginAPI.google_verifier.verify"])
        self.assertEqual([s["module"] for s in google["mutation_sites"]],
                         ["google_login_challenges.py", "sessions.py"])
        team = _delegate(report, "team_wsgi", "change_current")
        self.assertEqual([s["sqlite_context_line"] for s in team["mutation_sites"]],
                         [114, 114, 114])
        invite = _delegate(report, "invitation_wsgi", "invite_current")
        self.assertEqual(invite["unresolved_dependencies"], ["BusinessInvitations.deliver"])
        self.assertEqual([s["sqlite_context_line"] for s in invite["mutation_sites"]],
                         [162, 186, 186, 197, 197])
        redeem = _delegate(report, "invitation_accept_wsgi", "redeem_invitation_google")
        self.assertEqual(redeem["unresolved_dependencies"], google["unresolved_dependencies"])
        self.assertEqual([s["sqlite_context_line"] for s in redeem["mutation_sites"]],
                         [40, 256, 256, 256, 67, 51])

    def test_editorial_mutations_keep_transaction_boundaries(self):
        report = inspect_ci_wsgi_write_boundaries()
        for handler, method, path, context, lines in (
            ("preference_write_wsgi", "set_posting_preferences", "posting_preferences.py", 65, [66]),
            ("calendar_wsgi", "propose", "calendar_proposals.py", 142, [144, 156]),
            ("calendar_wsgi", "discard", "calendar_proposals.py", 266, [267]),
            ("review_feedback_wsgi", "save", "review_feedback.py", 125, [131, 138, 148]),
            ("review_feedback_wsgi", "discard", "review_feedback.py", 166, [174, 179]),
            ("facts_write_wsgi", "confirm", "ai_business_facts.py", 38, [44]),
            ("ai_memory_wsgi", "edit_ai_memory", "ai_account_policy.py", 134, [135, 139]),
            ("ai_draft_edit_wsgi", "edit_ai_draft_component", "ai_content_drafts.py", 102, [103, 114]),
        ):
            with self.subTest(handler=handler, method=method):
                call = _delegate(report, handler, method)
                self.assertEqual(call["boundary_status"], "reviewed_source_write_path")
                self.assertEqual(
                    [(site["module"], site["sqlite_context_line"], site["line"])
                     for site in call["mutation_sites"]],
                    [(path, context, line) for line in lines],
                )
        draft_edit = _delegate(report, "ai_draft_edit_wsgi", "edit_ai_draft_component")
        self.assertEqual(draft_edit["mutation_sites"][1]["kind"],
                         "sql_delete_on_image_prompt_edit")

    def test_read_previews_do_not_imply_paid_generation_coverage(self):
        report = inspect_ci_wsgi_write_boundaries()
        for handler, method in (
            ("calendar_wsgi", "readiness_digest"),
            ("calendar_wsgi", "suggest_unassigned"),
            ("review_feedback_wsgi", "history_current_business"),
            ("review_readiness_wsgi", "list_current_business"),
            ("ai_batch_preview_wsgi", "preview_ai_batch"),
        ):
            with self.subTest(handler=handler, method=method):
                call = _delegate(report, handler, method)
                self.assertEqual(call["boundary_status"], "no_direct_mutation_in_reviewed_body")
                self.assertEqual(call["mutation_sites"], [])
        attributes = {handler["gateway_attribute"] for handler in report["handler_candidates"]}
        self.assertIn("ai_batch_preview_wsgi", attributes)
        self.assertNotIn("generate_app", attributes)
        self.assertNotIn("revision_app", attributes)
        self.assertFalse(report["deployed_writer_inventory_complete"])

    def test_preview_source_drift_withholds_read_classification(self):
        root = self._fixture()
        path = root / "ai_batch_preview.py"
        path.write_text(path.read_text().replace(
            "facts=self.facts.snapshot(", "facts=self.facts.dynamic_snapshot("))
        report = inspect_ci_wsgi_write_boundaries(source_root=root)
        self.assertEqual(report["drifted_reviewed_source"], ["ai_batch_preview.py"])
        call = _delegate(report, "ai_batch_preview_wsgi", "preview_ai_batch")
        self.assertEqual(call["boundary_status"], "reviewed_source_drift")
        self.assertEqual(call["source_chain"], [])

    def test_rebound_local_alias_withholds_mapping(self):
        root = self._fixture()
        handler = root / "bam_local_draft_wsgi.py"
        handler.write_text(handler.read_text().replace(
            "result=create(session_token=", "result=self.other_handler(session_token="))
        report = inspect_ci_wsgi_write_boundaries(source_root=root)
        self.assertEqual(report["drifted_reviewed_source"], ["bam_local_draft_wsgi.py"])
        for candidate in report["handler_candidates"]:
            for call in candidate["manually_reviewed_alias_calls"]:
                self.assertEqual(call["boundary_status"], "reviewed_source_drift")
                self.assertEqual(call["mutation_sites"], [])

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
