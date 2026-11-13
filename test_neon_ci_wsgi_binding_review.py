"""CI-only candidate WSGI binding source-regression tests."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from neon_ci_wsgi_binding_review import inspect_ci_wsgi_handler_bindings


class TestCIWSGIBindings(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {"BAM_EPHEMERAL_PG_TEST": "1"})
        env.start()
        self.addCleanup(env.stop)

    def fixture(self, sources):
        tmp = tempfile.TemporaryDirectory(prefix="bam_ci_wsgi_")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        for filename, content in sources.items():
            (root / filename).write_text(content, encoding="utf-8")
        return root

    def test_aliased_handler_binding_and_guard_clues(self):
        root = self.fixture({
            "gateway_wsgi.py": """
from handler_wsgi import Handler as Service
_ROUTES = frozenset(('/api/v1/test-a','/api/v1/test-b'))
class Gateway:
 def __init__(self):
  self.write_wsgi = Service()
  self.other_wsgi = object()
 def __call__(self, env, reply):
  if env.get('PATH_INFO') in _ROUTES and env.get('REQUEST_METHOD')=='PUT':
   return self.write_wsgi(env,reply)
  return self.other_wsgi(env,reply)
""",
            "handler_wsgi.py": """
class Handler:
 def __call__(self, env, reply):
  db.execute('INSERT INTO synthetic VALUES (1)')
""",
        })
        report = inspect_ci_wsgi_handler_bindings(source_root=root,
                                                  gateway_file="gateway_wsgi.py")
        calls = report["gateway_classes"][0]["calls"]
        self.assertEqual(report["candidate_handler_calls"], 2)
        self.assertEqual(calls[0]["binding_status"], "declared_class_candidate")
        self.assertEqual(calls[0]["candidate_constructors"][0]["module"], "handler_wsgi")
        self.assertEqual(calls[0]["candidate_constructors"][0]["class"], "Handler")
        self.assertEqual(calls[0]["conditional_route_hints"],
                         ["/api/v1/test-a", "/api/v1/test-b"])
        self.assertEqual(calls[0]["conditional_method_hints"], ["PUT"])
        self.assertEqual(calls[1]["binding_status"], "unresolved_constructor")
        self.assertEqual(report["review_sha256"], inspect_ci_wsgi_handler_bindings(
            source_root=root, gateway_file="gateway_wsgi.py")["review_sha256"])
        self.assertFalse(report["complete_writer_coverage_proven"])
        self.assertFalse(report["migration_or_cutover_permitted"])

    def test_ambiguous_and_unbound_dispatch_reported(self):
        root = self.fixture({"gateway_wsgi.py": """
class Handler: pass
class Gateway:
 def __init__(self):
  self.auth_wsgi = Handler()
  self.auth_wsgi = getattr(self,'other')
 def __call__(self, env, reply):
  return self.auth_wsgi(env, reply)
"""})
        old = inspect_ci_wsgi_handler_bindings(source_root=root,
                                               gateway_file="gateway_wsgi.py")
        self.assertEqual(old["gateway_classes"][0]["calls"][0]["binding_status"],
                         "ambiguous")
        (root / "gateway_wsgi.py").write_text("""
class Gateway:
 def __call__(self, env, reply):
  return self.unbound_wsgi(env, reply)
""", encoding="utf-8")
        new = inspect_ci_wsgi_handler_bindings(source_root=root,
                                               gateway_file="gateway_wsgi.py")
        self.assertNotEqual(old["review_sha256"], new["review_sha256"])
        self.assertEqual(new["gateway_classes"][0]["calls"][0]["binding_status"],
                         "unbound")

    def test_ci_disabled_symlink_and_bad_syntax_fail_closed(self):
        root = self.fixture({"gateway_wsgi.py": """
class Gateway:
 def __call__(self, env, reply):
  return self.missing_wsgi(env, reply)
"""})
        with patch.dict(os.environ, {"BAM_EPHEMERAL_PG_TEST": "0"}):
            with self.assertRaises(PermissionError):
                inspect_ci_wsgi_handler_bindings(
                    source_root=root, gateway_file="gateway_wsgi.py")
        with self.assertRaises(ValueError):
            inspect_ci_wsgi_handler_bindings(
                source_root=root, gateway_file="../gateway_wsgi.py")
        (root / "link.py").symlink_to(root / "gateway_wsgi.py")
        with self.assertRaises(PermissionError):
            inspect_ci_wsgi_handler_bindings(
                source_root=root, gateway_file="gateway_wsgi.py")
        (root / "link.py").unlink()
        (root / "gateway_wsgi.py").write_text("def invalid(:\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            inspect_ci_wsgi_handler_bindings(
                source_root=root, gateway_file="gateway_wsgi.py")

    def test_real_checkout_emits_hypotheses_not_readiness(self):
        report = inspect_ci_wsgi_handler_bindings()
        self.assertGreater(report["candidate_handler_calls"], 15)
        cls = next(c for c in report["gateway_classes"]
                   if c["gateway_class"] == "BAMOfflineGateway")
        names = {c["attribute"] for c in cls["calls"]}
        for name in ("auth_wsgi", "content_write_wsgi", "team_wsgi",
                     "pending_media_wsgi", "calendar_wsgi"):
            self.assertIn(name, names)
        self.assertFalse(report["runtime_rebinding_or_deployment_covered"])
        self.assertFalse(report["tenant_transaction_checks_proven"])
        self.assertFalse(report["private_beta_ready"])
        self.assertFalse(report["publishing_enabled"])


if __name__ == "__main__":
    unittest.main()
