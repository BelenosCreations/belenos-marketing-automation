"""Adversarial offline source-inventory tests; no customer data or services."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from neon_static_writer_surface_inventory import inspect_ci_python_writer_surfaces


class TestCIWriterSurfaceInventory(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"BAM_EPHEMERAL_PG_TEST": "1"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def _fixture(self, filenames):
        tmp = tempfile.TemporaryDirectory(prefix="bam_ci_source_")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        for name, content in filenames.items():
            (root / name).write_text(content, encoding="utf-8")
        return root

    def test_real_checkout_review_is_read_only_and_reports_blockers(self):
        result = inspect_ci_python_writer_surfaces()
        names = {entry["module"] for entry in result["entries"]}
        self.assertIn("sessions.py", names)
        self.assertIn("bam_offline_gateway.py", names)
        self.assertIn("bam_auth_wsgi.py", names)
        self.assertIn("dev_http_gateway.py", names)
        self.assertGreater(result["scanned_python_module_count"], 100)
        self.assertGreater(result["possible_sql_mutations"], 10)
        self.assertGreater(result["possible_wsgi_modules"], 10)
        self.assertFalse(result["complete_writer_coverage_proven"])
        self.assertFalse(result["all_worker_and_callback_writers_fenced"])
        self.assertFalse(result["postgres_connection_attempted"])
        self.assertFalse(result["cutover_permitted"])
        self.assertFalse(result["publishing_enabled"])
        self.assertRegex(result["inventory_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(result["inventory_sha256"],
                         inspect_ci_python_writer_surfaces()["inventory_sha256"])

    def test_fixture_classifies_writes_reads_unknown_callbacks_and_http(self):
        root = self._fixture({
            "demo_wsgi.py": """
class Demo:
    def __call__(self, environ, start_response):
        db.execute('INSERT INTO x VALUES (1)')
        db.execute('SELECT * FROM x')
        db.execute(dynamic_statement)
        db.commit()
        open('demo', 'wb')
        route='/api/v1/test'
    def webhook_event(self):
        pass
""",
            "worker.py": """
def run_job():
    db.executemany('DELETE FROM x WHERE id=?', [(1,)])
    db.rollback()
""",
            "test_ignored.py": "raise SyntaxError('should not run')",
        })
        report = inspect_ci_python_writer_surfaces(source_root=root)
        self.assertEqual(report["scanned_python_module_count"], 2)
        found = {e["module"]: e for e in report["entries"]}
        signs = {s["kind"] for s in found["demo_wsgi.py"]["signals"]}
        self.assertTrue({"wsgi_dispatch", "sql_write:insert",
                         "sql_read:select", "sql_unknown",
                         "transaction_commit", "filesystem_open_write",
                         "possible_callback"} <= signs)
        self.assertEqual(found["demo_wsgi.py"]["routes"], ["/api/v1/test"])
        self.assertIn("possible_scheduled_job",
                      found["worker.py"]["entrypoint_flags"])

    def test_source_mutation_changes_digest_without_side_effects(self):
        root = self._fixture({"store.py": "db.execute('INSERT INTO t VALUES (1)')"})
        a = inspect_ci_python_writer_surfaces(source_root=root)
        (root / "store.py").write_text(
            "db.execute('INSERT INTO t VALUES (2)')", encoding="utf-8")
        b = inspect_ci_python_writer_surfaces(source_root=root)
        self.assertNotEqual(a["inventory_sha256"], b["inventory_sha256"])
        self.assertEqual(a["possible_sql_mutations"], b["possible_sql_mutations"])

    def test_untrusted_source_rejected_not_imported(self):
        root = self._fixture({"sink.py": "db.commit()\n__import__('os').system('false')\n"})
        self.assertFalse(any(s["kind"].startswith("sql_") for s in
                         inspect_ci_python_writer_surfaces(
                             source_root=root)["entries"][0]["signals"])
        )
        (root / "sink.py").write_text("def bad(:\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            inspect_ci_python_writer_surfaces(source_root=root)

    def test_symlink_and_hardlink_sources_rejected(self):
        root = self._fixture({"safe.py": "db.commit()\n"})
        (root / "linked.py").symlink_to(root / "safe.py")
        with self.assertRaises(PermissionError):
            inspect_ci_python_writer_surfaces(source_root=root)
        (root / "linked.py").unlink()
        os.link(root / "safe.py", root / "linked.py")
        with self.assertRaises(PermissionError):
            inspect_ci_python_writer_surfaces(source_root=root)

    def test_disabled_without_explicit_ci_gate(self):
        root = self._fixture({"w.py": "db.commit()\n"})
        with patch.dict(os.environ, {"BAM_EPHEMERAL_PG_TEST": "0"}):
            with self.assertRaises(PermissionError):
                inspect_ci_python_writer_surfaces(source_root=root)

    def test_dynamic_sql_is_never_reported_as_read_only(self):
        root = self._fixture({"query.py": """
db.execute('WITH x AS (SELECT 1) UPDATE t SET a=2')
db.execute('/*comment*/SELECT 1')
db.executescript('SELECT 1; DROP TABLE t;')
"""})
        report = inspect_ci_python_writer_surfaces(source_root=root)
        self.assertEqual(report["unresolved_sql_sites"], 3)


if __name__ == "__main__":
    unittest.main()
