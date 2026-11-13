"""CI-only, non-executing candidate WSGI-handler-to-service call inventory.

This syntactic review neither executes code nor proves actual request reachability,
tenant authorization, SQL commits, epoch fencing, or deployed writer coverage.
"""
import ast
import hashlib
import json
from pathlib import Path
import re

from neon_ci_wsgi_binding_review import (
    inspect_ci_wsgi_handler_bindings, _read,
)


def _fingerprint(data):
    raw = json.dumps(data, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


class _DelegateCalls(ast.NodeVisitor):
    def __init__(self, assigned):
        self.assigned = assigned
        self.calls = []

    def visit_FunctionDef(self, node):
        pass

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Lambda(self, node):
        pass

    def visit_Call(self, node):
        func = node.func
        if (isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Attribute)
                and isinstance(func.value.value, ast.Name)
                and func.value.value.id == "self"):
            dependency = func.value.attr
            if not func.attr.startswith("__"):
                self.calls.append({
                    "line": node.lineno,
                    "dependency_attribute": dependency,
                    "candidate_method": func.attr,
                    "constructor_dependency_hint":
                        self.assigned.get(dependency, "unresolved"),
                    "actual_service_or_write_proven": False,
                })
        self.generic_visit(node)


def _handler_methods(tree, class_name):
    cls = next((x for x in tree.body if isinstance(x, ast.ClassDef)
                and x.name == class_name), None)
    if cls is None:
        return [], "class_missing"
    init = next((x for x in cls.body if isinstance(x, ast.FunctionDef)
                 and x.name == "__init__"), None)
    call = next((x for x in cls.body if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and x.name == "__call__"), None)
    if call is None:
        return [], "handler_call_missing"
    assigned = {}
    if init is not None:
        params = {p.arg for p in (init.args.posonlyargs +
                                 init.args.args + init.args.kwonlyargs)}
        for node in ast.walk(init):
            if isinstance(node, ast.Assign):
                targets, value = node.targets, node.value
            elif isinstance(node, ast.AnnAssign):
                targets, value = [node.target], node.value
            else:
                continue
            if not (isinstance(value, ast.Name) and value.id in params):
                continue
            for target in targets:
                if (isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "self"):
                    assigned[target.attr] = "constructor_parameter:" + value.id
    visitor = _DelegateCalls(assigned)
    for statement in call.body:
        visitor.visit(statement)
    return sorted(visitor.calls, key=lambda x: (
        x["line"], x["dependency_attribute"], x["candidate_method"])), "candidate"


def inspect_ci_wsgi_delegated_calls(*, source_root=None,
                                     gateway_file="bam_offline_gateway.py"):
    """Review a bounded single gateway-to-handler-to-method syntactic hop."""
    gateway_report = inspect_ci_wsgi_handler_bindings(
        source_root=source_root, gateway_file=gateway_file)
    root = Path(__file__).resolve().parent if source_root is None else Path(source_root)
    handlers = []
    source_hashes = {}
    for gateway in gateway_report["gateway_classes"]:
        for call in gateway["calls"]:
            for candidate in call["candidate_constructors"]:
                module = candidate["module"]
                klass = candidate["class"]
                if (type(module) is not str or type(klass) is not str or
                        not re.fullmatch(r"[A-Za-z0-9_]+", module)):
                    status, calls = "unresolved_candidate", []
                else:
                    path = root / (module + ".py")
                    if not path.exists():
                        status, calls = "module_missing", []
                    else:
                        tree, sha = _read(path)
                        source_hashes[module] = sha
                        calls, status = _handler_methods(tree, klass)
                handlers.append({
                    "gateway_class": gateway["gateway_class"],
                    "gateway_attribute": call["attribute"],
                    "gateway_line": call["line"],
                    "route_hints": call["conditional_route_hints"],
                    "method_hints": call["conditional_method_hints"],
                    "binding_status": call["binding_status"],
                    "handler_module": module,
                    "handler_class": klass,
                    "handler_source_status": status,
                    "syntactic_delegate_calls": calls,
                })
            if not call["candidate_constructors"]:
                handlers.append({
                    "gateway_class": gateway["gateway_class"],
                    "gateway_attribute": call["attribute"],
                    "gateway_line": call["line"],
                    "route_hints": call["conditional_route_hints"],
                    "method_hints": call["conditional_method_hints"],
                    "binding_status": "unbound",
                    "handler_module": None, "handler_class": None,
                    "handler_source_status": "unresolved_candidate",
                    "syntactic_delegate_calls": [],
                })
    evidence = {
        "format": "bam-ci-wsgi-service-delegation-hints-v1",
        "source_gateway_review_sha256": gateway_report["review_sha256"],
        "handler_source_sha256": {name: source_hashes[name]
                                  for name in sorted(source_hashes)},
        "handler_candidates": handlers,
    }
    return {
        **evidence,
        "review_sha256": _fingerprint(evidence),
        "candidate_handler_bindings": len(handlers),
        "candidate_service_method_calls": sum(
            len(h["syntactic_delegate_calls"]) for h in handlers),
        "indirect_dynamic_service_writers_fully_mapped": False,
        "runtime_gateway_handler_binding_verified": False,
        "authoritative_tenant_security_proven": False,
        "postgresql_generation_fencing_proven": False,
        "production_database_read_or_migration": False,
        "independent_operator_or_backup_verified": False,
        "private_beta_ready": False,
        "publishing_enabled": False,
    }
