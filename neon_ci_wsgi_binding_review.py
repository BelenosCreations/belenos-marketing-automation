"""CI-only AST review of candidate WSGI handler bindings; no execution.

Do not interpret source hypotheses as deployed coverage, tenant protection,
persistent migration fencing or operator approval.
"""
import ast
import hashlib
import json
from pathlib import Path
import re
import stat
from neon_static_writer_surface_inventory import inspect_ci_python_writer_surfaces

_ROUTE = re.compile(r"^/api/[a-z0-9_/-]+\Z")
_METHODS = frozenset(("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"))


def _digest(obj):
    data = json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode("ascii")
    return hashlib.sha256(data).hexdigest()


def _read(path):
    meta = path.lstat()
    if not stat.S_ISREG(meta.st_mode) or meta.st_nlink != 1 or meta.st_size > 1048576:
        raise PermissionError("Unsafe candidate source file")
    raw = path.read_bytes()
    if len(raw) > 1048576:
        raise PermissionError("Oversized candidate source")
    try:
        tree = ast.parse(raw.decode("utf-8"), filename=path.name)
    except (SyntaxError, UnicodeDecodeError) as exc:
        raise ValueError("Unparseable candidate source") from exc
    return tree, hashlib.sha256(raw).hexdigest()


def _self_name(node):
    if (isinstance(node, ast.Attribute) and
            isinstance(node.value, ast.Name) and node.value.id == "self"):
        return node.attr
    return None


def _constructor(node):
    return (node.func.id if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name) else None)


def _route_clues(node, tables):
    if isinstance(node, ast.Constant) and type(node.value) is str:
        return {node.value} if _ROUTE.fullmatch(node.value) else set()
    if isinstance(node, ast.Name):
        return set(tables.get(node.id, ()))
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return set().union(*(_route_clues(x, tables) for x in node.elts))
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id in ("frozenset", "tuple", "set", "list")
            and len(node.args) == 1 and not node.keywords):
        return _route_clues(node.args[0], tables)
    return set()


class _Calls(ast.NodeVisitor):
    def __init__(self, assignments, tables):
        self.assignments = assignments
        self.tables = tables
        self.guards = []
        self.found = []

    def visit_FunctionDef(self, node):
        pass

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Lambda(self, node):
        pass

    def visit_If(self, node):
        literal_routes = sorted(set().union(*(
            _route_clues(x, self.tables) for x in ast.walk(node.test))))
        literal_methods = sorted({x.value for x in ast.walk(node.test)
                                  if isinstance(x, ast.Constant) and
                                  type(x.value) is str and x.value in _METHODS})
        self.visit(node.test)
        for branch, statements in (("if", node.body), ("else", node.orelse)):
            self.guards.append((branch, literal_routes, literal_methods))
            for statement in statements:
                self.visit(statement)
            self.guards.pop()

    def visit_Call(self, node):
        attr = _self_name(node.func)
        if attr is not None and (attr.endswith("_wsgi") or attr in self.assignments):
            choices = sorted(self.assignments.get(attr, []),
                             key=lambda x: (x["line"], x["status"]))
            status = ("unbound" if not choices else
                      "ambiguous" if len(choices) != 1 else choices[0]["status"])
            self.found.append({
                "line": node.lineno,
                "attribute": attr,
                "binding_status": status,
                "candidate_constructors": choices,
                "conditional_route_hints": sorted({
                    r for _, routes, _ in self.guards for r in routes}),
                "conditional_method_hints": sorted({
                    m for _, _, methods in self.guards for m in methods}),
                "branch_hints": [x[0] for x in self.guards],
                "runtime_execution_proven": False,
            })
        self.generic_visit(node)


def inspect_ci_wsgi_handler_bindings(*, source_root=None,
                                      gateway_file="bam_offline_gateway.py"):
    """Review only top-level files under the existing CI file-safety gate."""
    inventory = inspect_ci_python_writer_surfaces(source_root=source_root)
    if type(gateway_file) is not str or not re.fullmatch(
            r"[a-zA-Z0-9_]+\.py", gateway_file):
        raise ValueError("Top-level gateway module required")
    root = (Path(__file__).resolve().parent if source_root is None
            else Path(source_root))
    files = {p.name: p for p in root.glob("*.py")
             if not p.name.startswith("test_")}
    if gateway_file not in files:
        raise ValueError("Unknown candidate gateway")
    gateway, gate_sha = _read(files[gateway_file])
    expected = next((x["source_sha256"] for x in inventory["entries"]
                     if x["module"] == gateway_file), None)
    if gate_sha != expected:
        raise ValueError("Gateway changed during source inspection")
    declared_classes = {}
    imported_aliases = {}
    for filename, path in sorted(files.items()):
        tree, _ = _read(path)
        declared_classes[filename[:-3]] = {
            x.name for x in tree.body if isinstance(x, ast.ClassDef)}
        if filename == gateway_file:
            for node in tree.body:
                if (isinstance(node, ast.ImportFrom) and
                        node.level == 0 and node.module):
                    for alias in node.names:
                        if alias.name != "*":
                            imported_aliases[alias.asname or alias.name] = (
                                node.module, alias.name)
    tables = {}
    for node in gateway.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)):
            tables[node.targets[0].id] = sorted(_route_clues(node.value, tables))
    result = []
    for cl in gateway.body:
        if not isinstance(cl, ast.ClassDef):
            continue
        init = next((x for x in cl.body if isinstance(x, ast.FunctionDef)
                     and x.name == "__init__"), None)
        call = next((x for x in cl.body if isinstance(
            x, (ast.FunctionDef, ast.AsyncFunctionDef)) and x.name == "__call__"), None)
        if call is None:
            continue
        assigned = {}
        if init:
            for node in ast.walk(init):
                if isinstance(node, ast.Assign):
                    targets, value = node.targets, node.value
                elif isinstance(node, ast.AnnAssign):
                    targets, value = [node.target], node.value
                else:
                    continue
                for target in targets:
                    attr = _self_name(target)
                    if attr is None:
                        continue
                    constructor = _constructor(value)
                    module, klass = imported_aliases.get(
                        constructor, (gateway_file[:-3], constructor))
                    declared = bool(constructor and
                                    klass in declared_classes.get(module, set()))
                    assigned.setdefault(attr, []).append({
                        "line": node.lineno,
                        "module": module if constructor else None,
                        "class": klass if constructor else None,
                        "status": ("declared_class_candidate" if declared
                                   else "unresolved_constructor"),
                    })
        visitor = _Calls(assigned, tables)
        for stmt in call.body:
            visitor.visit(stmt)
        result.append({
            "gateway_class": cl.name,
            "dispatch_scope": gateway_file[:-3] + "::" + cl.name + ".__call__",
            "calls": sorted(visitor.found,
                            key=lambda x: (x["line"], x["attribute"])),
        })
    if not result:
        raise ValueError("No candidate WSGI dispatcher")
    evidence = {
        "format": "bam-ci-source-wsgi-binding-v1",
        "source_inventory_sha256": inventory["inventory_sha256"],
        "gateway_source_sha256": gate_sha,
        "gateway_file": gateway_file,
        "gateway_classes": result,
    }
    found = [c for cl in result for c in cl["calls"]]
    return {
        **evidence, "review_sha256": _digest(evidence),
        "candidate_handler_calls": len(found),
        "unresolved_or_ambiguous_calls": sum(
            c["binding_status"] != "declared_class_candidate" for c in found),
        "runtime_rebinding_or_deployment_covered": False,
        "complete_writer_coverage_proven": False,
        "tenant_transaction_checks_proven": False,
        "persistent_epoch_authority_proven": False,
        "operator_approved": False,
        "customer_data_read": False,
        "postgres_connection_attempted": False,
        "migration_or_cutover_permitted": False,
        "private_beta_ready": False,
        "publishing_enabled": False,
    }
