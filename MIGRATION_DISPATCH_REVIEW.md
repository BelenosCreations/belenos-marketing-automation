# CI-only candidate ingress-to-writer dispatch review

This is an **incomplete source review**, not runtime execution, route validation,
migration authority, or an application-wide writer fence. The CI-only
neon_static_writer_dispatch_review.py reads the same top-level Python source
set as the #102 AST inventory. It does not import project modules, connect to
PostgreSQL, open application databases, migrate data or call providers.

It suggests shortest possible direct-call paths from WSGI and candidate
callback/worker functions to SQL mutations, unknown SQL, filesystem writes,
transaction commits and job dispatches. It recognizes direct same-module
functions, same-class methods, and simple top-level import aliases. It also
records unresolved callable expressions and writer sites without a discovered
path. **An unmapped site is NOT evidence that a write is unreachable.** A
discovered path is only a syntax hypothesis; references may be rebound.

Run only with BAM_EPHEMERAL_PG_TEST=1 in a disposable checkout:

    python -m unittest test_neon_static_writer_dispatch_review -v

The report binds to the inventory SHA-256 and is independently hashed for
review. No report digest is an approval/signature, nor does the CI environment
flag authorize production work. Caller/route graphs are not deployed graphs.

## Explicit review gaps

- Dynamic dispatch, getattr(), dependency injection, monkeypatching, nested
  functions, decorators, reflection, descriptors, ORM calls and factory
  construction are unresolved or under-approximated.
- Cross-module traversals require simple import forms; local alias rebinding,
  star/relative imports, package imports and non-Python entry points are not
  covered. A synchronous function call is not proof a route invokes a write.
- Jobs, delayed retries, callbacks, service wrappers, startup hooks, provider
  SDKs, sub-processes, object stores and remote/hosted infrastructure require
  independent runtime and deployment inventories.
- There is no persistent shared transaction-bound generation authority,
  operator identity/approval, key custody, frozen-writer quiescence, restore,
  rollback, PostgreSQL cutover or production gate.
- The prior AST inventory inspects only top-level Python modules, and this
  dispatch review inherits that limitation. All surfaces must be
  independently enumerated before any live migration.

**Action required:** Have a reviewer reconcile every deployed route, WSGI
entry point, background job, provider callback/retry and alternative writer
against a versioned source/deployment inventory. Prove at the actual commit
boundary that all writers respect a shared, durable, independent generation
fence. Obtain independently approved migration semantics, restore and signed
operator transition evidence before any cutover planning can become active.

No customer data, Render, Neon, paid AI, social publishing, EdgePilot,
credential or hosting changes. Additional cost $0. Private Beta remains blocked.
