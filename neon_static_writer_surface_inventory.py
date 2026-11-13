"""CI-only static inventory of BAM Python writer and ingress surfaces.

Reads Python source files in the selected checkout; never imports them, calls
an application, opens a database, contacts a provider or grants a write fence.
Static signals are candidates for human review, NOT a proof of complete
application, WSGI, scheduled-task or provider-callback coverage.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import stat

_SQL_MUTATIONS = frozenset((
    "INSERT", "UPDATE", "DELETE", "REPLACE", "CREATE", "ALTER", "DROP",
    "TRUNCATE", "VACUUM", "REINDEX", "GRANT", "REVOKE", "MERGE",
))
_SQL_READS = frozenset(("SELECT", "EXPLAIN", "PRAGMA"))
_SQL_METHODS = frozenset(("execute", "executemany", "executescript"))
_TRANSACTION_METHODS = frozenset(("commit", "rollback", "begin"))
_FILE_METHODS = frozenset((
    "write_text", "write_bytes", "unlink", "rename", "replace",
    "mkdir", "rmdir", "remove", "makedirs",
))
_SCHEDULE_WORDS = ("schedule", "cron", "apscheduler", "celery", "background", "worker")
_CALLBACK_WORDS = ("callback", "webhook", "on_message", "on_event")
_ROUTE = re.compile(r"^/api/[a-z0-9_/-]+\Z")


def _require_ci():
    if os.environ.get("BAM_EPHEMERAL_PG_TEST") != "1":
        raise PermissionError("Source writer inventory is CI-only")


def _fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True).encode("ascii")).hexdigest()


def _sql_operation(call):
    if not call.args:
        return "unknown"
    try:
        sql = ast.literal_eval(call.args[0])
    except (ValueError, TypeError, MemoryError, RecursionError, SyntaxError):
        return "unknown"
    if type(sql) is not str:
        return "unknown"
    sql = sql.lstrip()
    # Comments, dynamic CTEs and multi-statement commands are deliberately
    # not promoted to known reads. Never mistake unknown SQL for read-only.
    if not sql or sql.startswith(("--", "/*")) or ";" in sql.rstrip(";"):
        return "unknown"
    word = sql.split(None, 1)[0].upper() if sql.split() else ""
    if word in _SQL_MUTATIONS:
        return "write:" + word.lower()
    if word in _SQL_READS:
        return "read:" + word.lower()
    return "unknown"


class _Collector(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.scope = []
        self.signals = []
        self.routes = set()
        self.classes = set()
        self.functions = set()

    def _signal(self, node, kind):
        self.signals.append({
            "line": node.lineno, "scope": ".".join(self.scope) or "<module>",
            "kind": kind,
        })

    def visit_ClassDef(self, node):
        self.classes.add(node.name)
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node):
        self.functions.add(node.name)
        if node.name.startswith("do_") and node.name in (
                "do_POST", "do_PUT", "do_PATCH", "do_DELETE"):
            self._signal(node, "http_mutation_handler")
        if node.name in ("__call__",) and (
                self.filename.endswith("_wsgi.py") or
                self.filename == "bam_offline_gateway.py"):
            self._signal(node, "wsgi_dispatch")
        if any(word in node.name.lower() for word in _CALLBACK_WORDS):
            self._signal(node, "possible_callback")
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Constant(self, node):
        if type(node.value) is str and _ROUTE.fullmatch(node.value):
            self.routes.add(node.value)

    def visit_Call(self, node):
        fun = node.func
        if isinstance(fun, ast.Attribute):
            name = fun.attr
            if name in _SQL_METHODS:
                operation = _sql_operation(node)
                if operation.startswith("read:"):
                    self._signal(node, "sql_" + operation)
                elif operation.startswith("write:"):
                    self._signal(node, "sql_" + operation)
                else:
                    self._signal(node, "sql_unknown")
            elif name in _TRANSACTION_METHODS:
                self._signal(node, "transaction_" + name)
            elif name in _FILE_METHODS:
                self._signal(node, "filesystem_" + name)
            elif name == "connect":
                self._signal(node, "possible_connection")
            elif name in ("submit", "apply_async", "enqueue", "delay"):
                self._signal(node, "possible_job_dispatch")
        elif isinstance(fun, ast.Name) and fun.id == "open":
            mode = None
            if len(node.args) > 1:
                try:
                    mode = ast.literal_eval(node.args[1])
                except (ValueError, TypeError, SyntaxError):
                    pass
            for keyword in node.keywords:
                if keyword.arg == "mode":
                    try:
                        mode = ast.literal_eval(keyword.value)
                    except (ValueError, TypeError, SyntaxError):
                        mode = None
            if mode is None or type(mode) is not str:
                self._signal(node, "filesystem_open_unknown")
            elif any(m in mode for m in "wax+"):
                self._signal(node, "filesystem_open_write")
        self.generic_visit(node)


def inspect_ci_python_writer_surfaces(*, source_root=None):
    """Return deterministic source-code evidence only, never authorizations.

    The optional path is for controlled CI fixtures. Only top-level *.py is
    inspected, so other languages, dynamically loaded code and external jobs
    necessarily remain out of scope. Each file must be regular and nonlinked.
    """
    _require_ci()
    if source_root is not None and not isinstance(source_root, (str, Path)):
        raise TypeError("CI source root must be a filesystem path")
    root = Path(__file__).resolve().parent if source_root is None else Path(source_root)
    directory = root.lstat()
    if not stat.S_ISDIR(directory.st_mode):
        raise PermissionError("Source root is not a directory")
    files = sorted(root.glob("*.py"))
    if not files:
        raise ValueError("No Python source modules for review")
    entries = []
    for path in files:
        if path.name.startswith("test_"):
            continue
        metadata = path.lstat()
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or
                metadata.st_size > 1024 * 1024):
            raise PermissionError("Unsafe source module for CI inventory")
        raw = path.read_bytes()
        try:
            tree = ast.parse(raw.decode("utf-8"), filename=path.name)
        except (UnicodeDecodeError, SyntaxError) as exc:
            raise ValueError("Unparseable Python source: " + path.name) from exc
        collector = _Collector(path.name)
        collector.visit(tree)
        # Imports are not executed; use naming as a weak scheduling/callback
        # discovery signal rather than asserting the absence of workers.
        lower = path.name.lower()
        flags = []
        if any(word in lower for word in _SCHEDULE_WORDS):
            flags.append("possible_scheduled_job")
        if any(word in lower for word in _CALLBACK_WORDS):
            flags.append("possible_provider_callback")
        if path.name.endswith("_wsgi.py") or path.name in (
                "bam_offline_gateway.py", "dev_http_gateway.py"):
            flags.append("possible_http_ingress")
        if collector.signals or collector.routes or flags:
            entries.append({
                "module": path.name,
                "source_sha256": hashlib.sha256(raw).hexdigest(),
                "signals": sorted(collector.signals,
                                  key=lambda x: (x["line"], x["kind"], x["scope"])),
                "routes": sorted(collector.routes),
                "entrypoint_flags": sorted(flags),
            })
    if not entries:
        raise ValueError("No candidate writer or ingress surfaces found")
    evidence = {"format": "bam-ci-python-writer-inventory-v1",
                "scanned_python_module_count": sum(
                    not x.name.startswith("test_") for x in files),
                "entries": entries}
    kinds = [s["kind"] for e in entries for s in e["signals"]]
    return {
        **evidence,
        "inventory_sha256": _fingerprint(evidence),
        "possible_sql_mutations": sum(k.startswith("sql_write:") for k in kinds),
        "unresolved_sql_sites": kinds.count("sql_unknown"),
        "possible_wsgi_modules": sum(
            "possible_http_ingress" in e["entrypoint_flags"] for e in entries),
        "possible_scheduler_or_callback_modules": sum(
            any(flag in e["entrypoint_flags"] for flag in (
                "possible_scheduled_job", "possible_provider_callback"))
            for e in entries),
        "complete_writer_coverage_proven": False,
        "all_worker_and_callback_writers_fenced": False,
        "persistent_generation_authority_proven": False,
        "external_review_or_approval_proven": False,
        "postgres_connection_attempted": False,
        "customer_data_read": False,
        "cutover_permitted": False,
        "production_ready": False,
        "publishing_enabled": False,
    }
