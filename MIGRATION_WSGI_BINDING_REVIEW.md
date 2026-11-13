# CI-only WSGI handler binding-source review

PR #107 extends the independently verified #106 review. The module
neon_ci_wsgi_binding_review.py is guarded by the same CI opt-in source scanner
as PR #102 and runs AST parsing only. It never imports application modules,
calls WSGI handlers, connects to production or disposable databases, moves
tenant data, makes provider calls or activates publishing.

For each __call__ method in the selected offline gateway module, the tool
reports possible direct self.attribute handler calls. It locates syntactic
assignments in __init__ and resolves simple absolute Python import aliases
to declared classes in source files. It reports literal API route and HTTP
method hints from surrounding if conditions without evaluating those
conditions or asserting route or authorization correctness. It includes source
digests and a stable review fingerprint; neither is a signed approval.

Synthetic tests cover import aliases, unresolved constructors, reassignments,
unknown attributes, source drift, CI-only gating and unsafe source rejection.

LIMITATIONS: dynamic dispatch, monkeypatching, attribute rebinding,
dependency injection, nested functions, relative imports, callbacks, scheduled
jobs, retry queues, middleware, non-Python writers and actual hosted traffic
remain unreviewed. A declared class hint is NOT proof of runtime reachability.
A missing link is NOT proof a writer is unreachable. No proof of tenant
isolation, session authentication, commit-time epoch fencing, or external
operator control exists. Independent deployment/worker inventory, persistent
generation authority, rollback, offsite backups and reviewed PostgreSQL
semantics remain mandatory before any real migration.

Run using the CI flag in an approved disposable checkout:
BAM_EPHEMERAL_PG_TEST=1 python -m unittest test_neon_ci_wsgi_binding_review -v

No customer migration, no Render/Neon/paid AI/EdgePilot/social activation, no
additional cost. Private Beta remains blocked and requires owner authorization.
PR #107 must pass exact-head and independently verified merged-main CI.
