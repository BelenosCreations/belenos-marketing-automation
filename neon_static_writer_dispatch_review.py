"""CI-only, conservative candidate call-path map for migration writer review.

This is source-text triage, not deployed call-graph completeness, runtime
reachability, generation fencing, application access, or migration approval.
No Python source is imported or executed.
"""
import ast
from collections import deque
import hashlib
import json
import os
from pathlib import Path

from neon_static_writer_surface_inventory import inspect_ci_python_writer_surfaces

_INGRESS_NAMES = {"application", "app", "__call__", "do_POST", "do_PUT",
                  "do_PATCH", "do_DELETE"}
_INGRESS_PARTS = ("callback", "webhook", "worker", "scheduled", "cron",
                  "job", "task")
_WRITER_PREFIXES = ("sql_write:", "sql_unknown", "filesystem_",
                    "transaction_commit", "possible_job_dispatch")
_MAX_TRACE_HOPS = 32
_MAX_TRACE_NODES = 4000
_MAX_EXAMPLES = 16


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
                                     separators=(",", ":")).encode("ascii")).hexdigest()


class _CallVisitor(ast.NodeVisitor):
    """Call syntax only; nested definitions are separate, not executed here."""
    def __init__(self):
        self.calls = []

    def visit_Call(self, node):
        self.calls.append(node.func)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        pass

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        pass

    def visit_Lambda(self, node):
        pass


def _called_from(statements):
    visitor = _CallVisitor()
    for stmt in statements:
        visitor.visit(stmt)
    return visitor.calls


def _name_of(call):
    if isinstance(call, ast.Name):
        return call.id
    if isinstance(call, ast.Attribute):
        return call.attr
    return "<dynamic>"


def inspect_ci_candidate_writer_paths(*, source_root=None):
    """Build deterministic possible paths, retaining unknowns and blockers.

    The inventory's CI gate, file size, regular-file and hardlink checks are
    mandatory. The analysis covers top-level Python modules only; it cannot
    resolve dependency injection, attribute rebinding, ORM, dynamic imports,
    runtime route tables, callbacks, external code or queued jobs.
    """
    inventory = inspect_ci_python_writer_surfaces(source_root=source_root)
    root = (Path(__file__).resolve().parent if source_root is None
            else Path(source_root))
    files = sorted(p for p in root.glob("*.py")
                   if not p.name.startswith("test_"))
    modules = {p.stem for p in files}
    nodes = {}
    local = {}
    classes = {}
    imported_modules = {}
    imported_functions = {}

    for path in files:
        module = path.stem
        tree = ast.parse(path.read_bytes().decode("utf-8"), filename=path.name)
        local[module] = {}
        classes[module] = set()
        imported_modules[module] = {}
        imported_functions[module] = {}
        nodes[module + "::<module>"] = (module, None, tree.body)
        for stmt in tree.body:
            if isinstance(stmt, ast.Import):
                for a in stmt.names:
                    alias = a.asname or a.name.split(".")[0]
                    # A dotted package is not a top-level repository module.
                    if a.name in modules:
                        imported_modules[module][alias] = a.name
            elif isinstance(stmt, ast.ImportFrom) and stmt.level == 0:
                if stmt.module in modules:
                    for a in stmt.names:
                        if a.name != "*":
                            imported_functions[module][a.asname or a.name] = (
                                stmt.module, a.name)
            elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                key = module + "::" + stmt.name
                nodes[key] = (module, None, stmt.body)
                local[module][stmt.name] = key
            elif isinstance(stmt, ast.ClassDef):
                classes[module].add(stmt.name)
                for child in stmt.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        key = module + "::" + stmt.name + "." + child.name
                        nodes[key] = (module, stmt.name, child.body)
                        local[module][stmt.name + "." + child.name] = key

    graph = {}
    unknown = {}
    for key, (module, class_name, body) in sorted(nodes.items()):
        edges, unresolved = set(), set()
        for call in _called_from(body):
            target = None
            if isinstance(call, ast.Name):
                name = call.id
                target = local[module].get(name)
                if target is None and name in imported_functions[module]:
                    m, f = imported_functions[module][name]
                    target = local[m].get(f)
            elif isinstance(call, ast.Attribute):
                attr = call.attr
                if isinstance(call.value, ast.Name):
                    owner = call.value.id
                    if owner in ("self", "cls") and class_name:
                        target = local[module].get(class_name + "." + attr)
                    elif owner in classes[module]:
                        target = local[module].get(owner + "." + attr)
                    elif owner in imported_modules[module]:
                        m = imported_modules[module][owner]
                        target = local[m].get(attr)
            if target in nodes:
                edges.add(target)
            else:
                unresolved.add(_name_of(call))
        graph[key] = sorted(edges)
        unknown[key] = sorted(unresolved)

    sinks = {}
    for entry in inventory["entries"]:
        module = entry["module"][:-3]
        for signal in entry["signals"]:
            kind = signal["kind"]
            if kind.startswith(_WRITER_PREFIXES):
                scope = signal["scope"]
                key = module + "::" + scope
                sinks.setdefault(key, []).append({"line": signal["line"],
                                                     "kind": kind})
    for signs in sinks.values():
        signs.sort(key=lambda x: (x["line"], x["kind"]))

    ingress = set()
    for entry in inventory["entries"]:
        module = entry["module"][:-3]
        if "possible_http_ingress" in entry["entrypoint_flags"]:
            ingress.add(module + "::<module>")
    for key in nodes:
        scope = key.split("::", 1)[1]
        short = scope.rsplit(".", 1)[-1]
        if (short in _INGRESS_NAMES or
                any(part in short.lower() for part in _INGRESS_PARTS)):
            ingress.add(key)

    paths = []
    reached = set()
    for starting in sorted(ingress & nodes.keys()):
        queue = deque([(starting, (starting,))])
        seen = set()
        found = []
        unresolved = set()
        truncated = False
        while queue:
            current, chain = queue.popleft()
            if current in seen:
                continue
            seen.add(current)
            if len(seen) > _MAX_TRACE_NODES:
                truncated = True
                break
            unresolved.update(unknown[current])
            if current in sinks:
                reached.add(current)
                for signal in sinks[current]:
                    found.append({"site": current, **signal, "path": list(chain)})
            if len(chain) >= _MAX_TRACE_HOPS:
                if graph[current]:
                    truncated = True
                continue
            for child in graph[current]:
                if child not in seen:
                    queue.append((child, chain + (child,)))
        found.sort(key=lambda x: (x["site"], x["line"], x["kind"], x["path"]))
        if found or unresolved or truncated:
            paths.append({
                "entrypoint": starting,
                "candidate_writer_site_count": len(found),
                "candidate_writer_paths": found[:_MAX_EXAMPLES],
                "omitted_writer_path_count": max(0, len(found) - _MAX_EXAMPLES),
                "unresolved_call_count": len(unresolved),
                "unresolved_call_examples": sorted(unresolved)[:_MAX_EXAMPLES],
                "traversal_truncated": truncated,
            })
    unmapped = [
        {"site": key, **signal}
        for key in sorted(sinks) if key not in reached
        for signal in sinks[key]
    ]
    evidence = {
        "format": "bam-ci-candidate-writer-call-paths-v1",
        "source_inventory_sha256": inventory["inventory_sha256"],
        "scanned_module_count": inventory["scanned_python_module_count"],
        "candidate_entrypoint_count": len(ingress),
        "candidate_writer_site_count": sum(map(len, sinks.values())),
        "entrypoint_review": paths,
        "unmapped_writer_candidates": unmapped,
    }
    return {
        **evidence,
        "review_sha256": _digest(evidence),
        "direct_call_edges_are_only_hypotheses": True,
        "dynamic_and_external_call_coverage_proven": False,
        "application_writer_fencing_proven": False,
        "independent_operator_approval_proven": False,
        "postgres_connection_attempted": False,
        "customer_data_read": False,
        "migration_or_cutover_permitted": False,
        "production_ready": False,
        "publishing_enabled": False,
    }
