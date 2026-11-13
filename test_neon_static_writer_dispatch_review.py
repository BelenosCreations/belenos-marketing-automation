"""No-network adversarial tests for candidate Python call-path discovery."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from neon_static_writer_dispatch_review import inspect_ci_candidate_writer_paths


class TestStaticDispatchReview(unittest.TestCase):
    def setUp(self):
        gate = patch.dict(os.environ, {"BAM_EPHEMERAL_PG_TEST": "1"})
        gate.start()
        self.addCleanup(gate.stop)

    def _fixture(self, contents):
        tmp = tempfile.TemporaryDirectory(prefix="bam_dispatch_ci_")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        for name, content in contents.items():
            (root / name).write_text(content, encoding="utf-8")
        return root

    def test_cross_module_import_alias_and_unmapped_writer_remain_visible(self):
        root = self._fixture({
            "app_wsgi.py": """
from handler import handle as dispatch
def application(environ, respond):
    return dispatch()
""",
            "handler.py": """
import store as storage
def handle():
    return storage.save()
""",
            "store.py": """
def save():
    db.execute('INSERT INTO ledger VALUES (1)')
""",
            "detached.py": """
def standalone():
    db.execute('DELETE FROM ledger')
""",
            "callbacks.py": """
def webhook_callback():
    db.execute(unknown_sql)
""",
        })
        report = inspect_ci_candidate_writer_paths(source_root=root)
        app = next(x for x in report["entrypoint_review"]
                   if x["entrypoint"] == "app_wsgi::application")
        self.assertEqual(app["candidate_writer_site_count"], 1)
        self.assertEqual(app["candidate_writer_paths"][0]["path"],
                         ["app_wsgi::application", "handler::handle",
                          "store::save"])
        self.assertIn({"site": "detached::standalone", "line": 3,
                       "kind": "sql_write:delete"},
                      report["unmapped_writer_candidates"])
        callback = next(x for x in report["entrypoint_review"]
                        if x["entrypoint"] == "callbacks::webhook_callback")
        self.assertEqual(callback["candidate_writer_paths"][0]["kind"],
                         "sql_unknown")
        self.assertTrue(report["direct_call_edges_are_only_hypotheses"])
        self.assertFalse(report["application_writer_fencing_proven"])
        self.assertFalse(report["migration_or_cutover_permitted"])
        self.assertFalse(report["publishing_enabled"])
        self.assertEqual(report["review_sha256"],
                         inspect_ci_candidate_writer_paths(
                             source_root=root)["review_sha256"])

    def test_self_method_and_synthetic_mutation_change_digest(self):
        root = self._fixture({"worker.py": """
class Worker:
    def worker_job(self):
        return self.persist()
    def persist(self):
        self.db.execute('UPDATE x SET a=1')
"""})
        a = inspect_ci_candidate_writer_paths(source_root=root)
        worker = next(x for x in a["entrypoint_review"]
                      if x["entrypoint"] == "worker::Worker.worker_job")
        self.assertEqual(worker["candidate_writer_paths"][0]["site"],
                         "worker::Worker.persist")
        (root / "worker.py").write_text("""
class Worker:
    def worker_job(self):
        return getattr(self, 'persist')()
    def persist(self):
        self.db.execute('UPDATE x SET a=1')
""", encoding="utf-8")
        b = inspect_ci_candidate_writer_paths(source_root=root)
        self.assertNotEqual(a["review_sha256"], b["review_sha256"])
        worker_b = next(x for x in b["entrypoint_review"]
                        if x["entrypoint"] == "worker::Worker.worker_job")
        self.assertEqual(worker_b["candidate_writer_site_count"], 0)
        self.assertGreater(worker_b["unresolved_call_count"], 0)
        self.assertIn({"site": "worker::Worker.persist", "line": 6,
                       "kind": "sql_write:update"},
                      b["unmapped_writer_candidates"])

    def test_symlinks_parse_errors_and_gate_fail_closed(self):
        root = self._fixture({"demo_wsgi.py":
                              "def application(env, respond):\n db.commit()\n"})
        with patch.dict(os.environ, {"BAM_EPHEMERAL_PG_TEST": "0"}):
            with self.assertRaises(PermissionError):
                inspect_ci_candidate_writer_paths(source_root=root)
        (root / "linked.py").symlink_to(root / "demo_wsgi.py")
        with self.assertRaises(PermissionError):
            inspect_ci_candidate_writer_paths(source_root=root)
        (root / "linked.py").unlink()
        (root / "demo_wsgi.py").write_text("def bad(:\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            inspect_ci_candidate_writer_paths(source_root=root)

    def test_actual_source_is_only_a_hypothesis_and_never_production_ready(self):
        report = inspect_ci_candidate_writer_paths()
        self.assertGreater(report["scanned_module_count"], 100)
        self.assertGreater(report["candidate_entrypoint_count"], 10)
        self.assertGreater(report["candidate_writer_site_count"], 10)
        self.assertRegex(report["review_sha256"], r"^[a-f0-9]{64}$")
        self.assertFalse(report["dynamic_and_external_call_coverage_proven"])
        self.assertFalse(report["independent_operator_approval_proven"])
        self.assertFalse(report["postgres_connection_attempted"])
        self.assertFalse(report["production_ready"])
        self.assertFalse(report["customer_data_read"])


if __name__ == "__main__":
    unittest.main()
