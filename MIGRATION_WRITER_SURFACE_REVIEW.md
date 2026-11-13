## Selected SQL and filesystem boundaries

The [held-draft and pending-media review](MIGRATION_WSGI_WRITE_BOUNDARY_REVIEW.md)
links selected local gateway delegates to their transaction and file sites.
It also records startup and alternative loopback writers, unresolved paths and
the remaining design work for database and media fencing.

## Candidate #105 static possible call-path triage

See MIGRATION_DISPATCH_REVIEW.md. CI-only basic direct-call mapping extends #102 source inventory but still misses dynamic, deployed and external write paths. Unknown and unmatched sites are review blockers, not proof of safety. Not a migration runner, global fence or production review approval.

## CI-only generation experiment after #102

Candidate #103 adds `neon_disposable_generation_authority.py` to model a
transaction-bound epoch check with private canary rows. The model must NOT be
mistaken for deployed, authoritative writer coverage. See
`MIGRATION_EPOCH_FENCE_REHEARSAL.md` for explicit crash, retry and
distributed-systems limitations.

# BAM inactive application writer-surface review

This document is a **source-code discovery artifact**, not a migration runner or
writer fence. The CI-gated `neon_static_writer_surface_inventory.py` parses top-level
BAM Python source modules without importing or executing them. It identifies
candidate SQLite SQL mutations, unknown SQL, transaction calls, file mutations,
WSGI/HTTP ingress, possible worker/callback filename hints, and route literals,
then computes a deterministic SHA-256 of the sanitized source inventory.

Run only in a disposable CI checkout with `BAM_EPHEMERAL_PG_TEST=1`; the normal
unittest suite checks known production-oriented *source* modules. Source text,
API tokens, full SQL strings and customer records are not returned. A fingerprint
is only a review comparison aid and not a trusted signer or authorization.

## Independent reviewer work still required

1. Review every candidate write and unknown SQL site, including indirect service
   calls from `bam_offline_gateway.py`, all `*_wsgi.py` modules and
   `dev_http_gateway.py`. The offline demo server and composition root are
   explicit entrypoints, not proof of a production system.
2. Enumerate all untracked or dynamically loaded Python, future scheduled jobs,
   provider webhooks, retry queues, independent deployed workers, subprocesses,
   filesystem/object writers, administrative jobs and non-Python clients.
3. Establish a separately controlled *persistent* generation/epoch authority.
   Every writer must acquire the active generation with a durable atomic
   compare-and-swap **at the write transaction boundary**, not only on HTTP
   admission; the DB must reject stale epochs/leases after restarts. Separate
   scoped permissions and read/write roles are necessary but insufficient.
4. Design disable/drain/observe behavior for callback retries and running jobs.
   Freeze new writes before source snapshot, verify quiescence, migrate only
   approved data, and prevent old writers from committing after promotion.
5. Independently custody operation IDs, latest journal head and signing keys;
   reject duplicate/reordered events and stale generations across crashed
   processes. Authenticate operator intent and enforce timeout/abort authority.
6. Rehearse dual-data-store cutover, failback, conflict resolution and
   rollback under crashed/stale workers, split brain and partitioned authority.
   Never silently unfreeze stale workers following recovery.
7. Require independently reviewed SQLite-to-PostgreSQL nullability, defaults,
   JSON, generated identity, foreign keys, tenant ownership, referential
   constraints and row-count parity. No automatic mapping approval.
8. Require off-host encrypted recoverable backups, independent key custody,
   verified restore and measured recovery performance before any production
   readiness claim.

**Known limitations:** static AST inspection misses dynamic SQL mutation
through wrappers, ORM use, SQL constructed in variables, runtime dispatch,
external services, JavaScript writers, non-top-level modules, function calls to
stateful services, and all untracked deployments. Even successful CI creates
no BAM-wide writer fence, no production generation authority, no operator
approval, no PostgreSQL connection, no backup, no cutover and no publishing.
The exact operator inventory must be reviewed out of band before authorizing
any real change. Additional cost $0; Render, Neon, social publishing, paid AI
and EdgePilot remain untouched.
