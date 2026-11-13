# BAM CI-only transaction-bound generation-fence rehearsal

Candidate PR #103 builds on independently verified PR #102, main SHA
`5ccff62cd27ffb2230026a8b008478a788e8c83f`, passed exact-head Actions
#43428652129 and independently passed merged-main Actions #43428902180.
Main/development were non-force synchronized 0/0 before this candidate.

`neon_disposable_generation_authority.py` demonstrates **local SQLite-only**
serializable ordering between a test canary writer and synthetic generation
transitions. All methods require the CI environment flag. The private 0600
fixture is automatically destroyed and cannot open an application database.

Key semantics:

- The writer checks expected epoch and `open` mode *inside the same
  `BEGIN IMMEDIATE` transaction* that inserts its synthetic canary.
- The freeze controller serializes under the same SQLite writer lock, compares
  an expected epoch and advances it to a persisted `frozen` generation.
- Reopening another connection retains `frozen` and rejects old epochs;
  an explicit synthetic resume advances generation again before new writes.
- Unique synthetic request IDs reject retries and replays, including after a
  connection is closed and reopened. Uncommitted writes roll back on close.
- All generation transitions and writes fail closed if the opt-in CI flag is
  absent. No customer tenants, payloads, credentials or provider calls.

Limitations requiring independent engineering review:

1. The fixture has **no independently authenticated administrator**, HMAC
   event chain or separately custodied epoch authority. Its database and
   controller share a single host/failure domain.
2. No actual BAM WSGI request, SQLite service, task worker, callback handler,
   file/object writer or PostgreSQL transaction checks this generation.
3. SQLite `BEGIN IMMEDIATE` ordering cannot establish distributed
   PostgreSQL advisory/row-lock semantics, real stale-instance fencing,
   network partition safety, authoritative role revocation or crash failover.
4. No real source-to-target mapping, customer data export, offsite encrypted
   backup, independently recoverable key, measured restore, cutover, rollback
   or production RPO/RTO is provided.
5. Tenant names are fabricated CI markers; no tenant authentication or
   runtime cross-tenant isolation is proven.

Before a real migration, require complete independently reviewed writer
inventory (see `MIGRATION_WRITER_SURFACE_REVIEW.md`), shared durable generation
authority, enforceable database-level transaction admission across every
writer, independently held latest heads/keys, authenticated operator control,
quiescence and retry drains, abort/rollback testing under failures, and
independently verified backups/restore. The eight-stage PostgreSQL preview
remains entirely inactive. Beta and publishing are blocked. $0 additional cost;
no Render, Neon, social, paid AI or EdgePilot infrastructure touched.
