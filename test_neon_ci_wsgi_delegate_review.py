"""Adversarial CI-only WSGI delegate-call source review."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from neon_ci_wsgi_delegate_review import inspect_ci_wsgi_delegated_calls


class TestWSGIDelegateReview(unittest.TestCase):
    def setUp(self):
        gate = patch.dict(os.environ, {"BAM_EPHEMERAL_PG_TEST": "1"})
        gate.start()
        self.addCleanup(gate.stop)

    def fixture(self, sources):
        tmp = tempfile.TemporaryDirectory(prefix="bam_delegate_ci_")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        for name, contents in sources.items():
            (root / name).write_text(contents, encoding="utf-8")
        return root

    def test_gateway_handler_service_chain_is_only_a_hint(self):
        root = self.fixture({
            "gateway_wsgi.py": """
from handler_wsgi import Handler
class Gateway:
 def __init__(self):
  self.write_wsgi = Handler(None)
 def __call__(self, env, respond):
  if env.get('PATH_INFO') == '/api/v1/write' and env.get('REQUEST_METHOD') == 'POST':
   return self.write_wsgi(env, respond)
""",
            "handler_wsgi.py": """
class Handler:
 def __init__(self, service):
  self.service = service
 def __call__(self, env, respond):
  return self.service.create_item(env)
""",
        })
        result = inspect_ci_wsgi_delegated_calls(
            source_root=root, gateway_file="gateway_wsgi.py")
        h = result["handler_candidates"][0]
        self.assertEqual(h["handler_module"], "handler_wsgi")
        self.assertEqual(h["handler_source_status"], "candidate")
        self.assertEqual(h["route_hints"], ["/api/v1/write"])
        self.assertEqual(h["method_hints"], ["POST"])
        self.assertEqual(h["syntactic_delegate_calls"][0]["candidate_method"],
                         "create_item")
        self.assertEqual(h["syntactic_delegate_calls"][0]["constructor_dependency_hint"],
                         "constructor_parameter:service")
        self.assertFalse(result["runtime_gateway_handler_binding_verified"])
        self.assertFalse(result["postgresql_generation_fencing_proven"])
        self.assertEqual(result["review_sha256"], inspect_ci_wsgi_delegated_calls(
            source_root=root, gateway_file="gateway_wsgi.py")["review_sha256"])

    def test_missing_and_dynamic_handler_are_unresolved(self):
        root = self.fixture({"gateway_wsgi.py": """
class Unresolved:
 def __init__(self):
  self.other_wsgi = unknown()
 def __call__(self, e, r):
  return self.other_wsgi(e, r)
"""})
        a = inspect_ci_wsgi_delegated_calls(
            source_root=root, gateway_file="gateway_wsgi.py")
        self.assertEqual(a["handler_candidates"][0]["handler_source_status"],
                         "unresolved_candidate")
        self.assertEqual(a["candidate_service_method_calls"], 0)
        self.assertFalse(a["private_beta_ready"])
        (root / "gateway_wsgi.py").write_text("""
class Unresolved:
 def __call__(self, e, r):
  return self.missing_wsgi(e, r)
""", encoding="utf-8")
        b = inspect_ci_wsgi_delegated_calls(
            source_root=root, gateway_file="gateway_wsgi.py")
        self.assertNotEqual(a["review_sha256"], b["review_sha256"])

    def test_ci_gate_and_source_safety(self):
        root = self.fixture({"gateway_wsgi.py": """
class G:
 def __call__(self, e, r): return self.fake_wsgi(e, r)
"""})
        with patch.dict(os.environ, {"BAM_EPHEMERAL_PG_TEST": "0"}):
            with self.assertRaises(PermissionError):
                inspect_ci_wsgi_delegated_calls(
                    source_root=root, gateway_file="gateway_wsgi.py")
        (root / "link_wsgi.py").symlink_to(root / "gateway_wsgi.py")
        with self.assertRaises(PermissionError):
            inspect_ci_wsgi_delegated_calls(
                source_root=root, gateway_file="gateway_wsgi.py")

    def test_real_checkout_exposes_content_and_media_delegate_candidates(self):
        report = inspect_ci_wsgi_delegated_calls()
        self.assertGreater(report["candidate_service_method_calls"], 5)
        content = next(h for h in report["handler_candidates"]
                       if h["handler_class"] == "BAMContentWriteWSGI")
        calls = {c["candidate_method"] for c in content["syntactic_delegate_calls"]}
        self.assertIn("create_held_draft", calls)
        self.assertIn("update_draft_hold", calls)
        media = next(h for h in report["handler_candidates"]
                     if h["handler_class"] == "BAMPendingMediaWSGI")
        methods = {c["candidate_method"] for c in media["syntactic_delegate_calls"]}
        self.assertIn("authorize_slot", methods)
        self.assertIn("receive", methods)
        self.assertFalse(report["indirect_dynamic_service_writers_fully_mapped"])
        self.assertFalse(report["private_beta_ready"])


if __name__ == "__main__":
    unittest.main()
