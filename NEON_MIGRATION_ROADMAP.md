# BAM SQLite → Neon PostgreSQL transition (offline preparation)

## Eighth reviewed PostgreSQL schema stage: attachment registry (candidate — November 12, 2026)

From verified PR #55 (main `508f5c2b`, Actions 43329651094 passed), add a distinct test-only PostgreSQL DDL preview for the existing nine-column `content_attachments` SQLite registry. Composite foreign key `(tenant_id,request_id)` references the exact draft's business and is backed by a unique composite index on `content_requests`. Status is constrained to pending/verified/rejected; hash format and MIME types have checks. The 47th reviewed preview table / eighth disposable CI migration remains **not** a production schema migration. Signed-in metadata-only status reads omit private storage paths and SHA-256 and do not perform scanning/verification. Real media uploads, secure object storage, malware/consent checks, backup integrity and all provider publication remain beta blockers. No Neon/Render service is provisioned by these tests.

## Authenticated scheduling preference reads and optimistic saves (November 12, 2026 candidate)

Building from verified PR #54 (`165a5398`, merged-main Actions 43328713423 passed), add a CI-only session-bound adapter for `scheduling_settings`. Its SQL verifies the hashed session, active/verified identity, current role and tenant on every read and write, with source-matching editor permissions. Persist manual weekday/timezone and smart preferred-hours preferences using an exact current revision CAS; a first save uses revision 0. Strictly validate IANA zone, bounded unique HH:MM weekday entries and hourly ranges before SQL. This is **not** a scheduler, queued job, provider write, verified audience recommendation, paid hosting, real Neon data migration or production authorization. Test with synthetic SQLite and disposable PostgreSQL before merge.

## Review feedback deletion/history parity (candidate — November 12, 2026)

Build on verified PR #53 (`25a99947`, full merged-main Actions 43326407161 passed). The CI-only PostgreSQL adapter now needs to match the source offline feedback's remaining versioned deletion and private owner/manager event-history read: scoped token-hash-checked DELETE by exact feedback version, followed by an independently authorized `removed` audit event in one atomic transaction. Audit events must remain after note removal and must carry **no prior note copy**. A bounded 50-event history checks role, active identity, tenant, session expiration/revocation on the SELECT. Denial, conflict, audit failure or duplicate action must fail closed and never touch publication state. Verify actual disposable PostgreSQL concurrency and SQLite parity. Production APIs, real Neon migration, encrypted backups, media storage and paid integrations remain separate unapproved work.

## Private review feedback SQL and audit in disposable PostgreSQL (November 12, 2026 candidate)

Starting from verified PR #52 (`ada3ee5b`, main CI 43325036530 passed), add role- and tenant-scoped read of private editorial notes and versioned owner/marketing-manager note writes. Every write checks the exact current held draft revision and expected feedback token, and an event describing the write must be inserted by the same live-authorized actor **within the same database transaction**. Missing event, stale version, bad role, expired/revoked session or duplicate note rolls back the write. Viewer/employee access is read-only, and feedback is explicitly not approval, scheduling or publish authority. These are synthetic disposable PostgreSQL and SQLite-source tests only; production database connections, public routes, email/social integrations, backup/restore and user data migration are out of scope until separate approval.

## Session-authenticated held draft writes in disposable PostgreSQL (candidate — November 12, 2026)

Build on verified PR #51 (`386efe5f`, merged-main CI 43317840660 passed): generate SQL-only, parameterized held-draft INSERT and optimistic draft text/guidance UPDATE, with active session token hash, current tenant, editor role, verified identity and session expiry/revocation checked in the *same* statement. All new drafts begin unapproved in `needs_content` state, provided media is empty, and only allowed text fields can be revised with revision compare-and-swap. The restricted CI adapter uses transaction-scoped execution and has no external connectivity, scheduler, approval/publish action, media upload, or paid AI. SQLite-source and real ephemeral PostgreSQL tests must cover hostile input, tenant isolation and concurrent editors before merge. Real Neon data migration, production pool/gateway, backups and beta access remain blocked pending separate engineering and user authorization.

## Owner-private collaboration roster read (candidate — November 12, 2026)

PR #50 is verified on merged main `dd0b3210`, Actions 43316746266 successful, with development synchronized. Add a read-only owner roster SQL contract to the disposable PostgreSQL CI adapter, compatible with the offline team roster's public fields. Same-statement current owner-session/membership checks protect member emails; unverified or disabled target email values remain redacted, and inactive membership remains visible to the owner for management. Current offline team-management mutations are **not** ported or enabled against Postgres. Validate local SQLite and ephemeral PostgreSQL role/tenant/revocation denial before PR/main merge. No customer data migration, provider API, public gateway or spending authorization.


## Held-draft inbox execution seam (candidate — November 12, 2026)

Starting from verified merged PR #49 (`e8b696cb`, main CI 43312549398 successful), add a tenant-bound list of held drafts to the **disposable CI-only** psycopg adapter. The query takes the hash of a validated session bearer, checks current active membership, session role, verified identity, expiry and revocation in the SELECT, and exposes a capped keyset page using stable creation-time/request-ID ordering. Filter values are allowlisted and parameterized; no customer credentials or draft data are exported. Real ephemeral PostgreSQL and offline SQLite tests are required before merging. This does not deliver a production query adapter, Neon migration, public API, media storage, publication or an authorization to spend money.


**Status: only partial schema blueprint, NO migration, NO Neon connection, no approved deployment.**

**Verified offline-only groundwork:** PR #30 (partial nine-table schema/DDL parity), PR #31 (all-table metadata inventory and prepared read SQL), PR #32 (privacy-safe local integrity checks) and PR #33 (priority CAS SQL preview) each passed exact merged-main GitHub Actions through `1c4ab9b7` (Actions 43218122644). **No Neon PostgreSQL connection or real migration exists.** Do not mistake placeholder-converted SQLite tests for PostgreSQL compatibility or production tenant isolation.

BAM's current alpha instantiates multiple SQLite-first service modules with `CREATE TABLE` statements, `PRAGMA table_info` checks and occasional SQLite-specific `AUTOINCREMENT`, `BEGIN IMMEDIATE` and `sqlite3.IntegrityError` handling. Passing unit tests in SQLite does not prove code will run on PostgreSQL. Never expose the offline gateway to Render or insert a PostgreSQL URL into its SQLite connection.

## Verified offline subset blueprint

`neon_schema_blueprint.py` contains **DDL preview only**, with no driver, network, credentials or execution switch, for nine of the existing alpha tables: identities, password credentials, Google identities, membership, sessions, account login failure tracking, held content requests, posting preferences and non-executable calendar proposals. It preserves the text/token hash and legacy JSON-string data representation for test parity; `BYTEA` replaces SQLite password digest/salt BLOB. `inspect_sqlite_subset` checks the live local schema's column names and publishes only table counts, schema digest and permanent readiness blockers, never credentials, user data or drafts. These are the **first nine tables of a larger schema**, not a deployable migration.

## Full local-table inventory and discrepancy gate

Run `python -m neon_schema_inventory` for a no-data, ephemeral initialized schema report. The inventory includes every non-internal SQLite table, the mapped nine-table subset, unported table names, counts of columns/indexes/foreign keys and review markers for autoincrement, BLOB conversion, foreign keys, CHECK semantics and TEXT columns. It never includes row data or SQL text. When new module tables are added, the schema digest and unmapped list change. Treat every unmapped table and query path as an open migration work item; index names and absence of markers do **not** mean SQL is PostgreSQL-compatible. Do not use this report to export or migrate user data.

## Prepared read-query seam (offline-only)

`neon_scoped_queries.py` defines placeholder-bound PostgreSQL SELECTs for held drafts and manual calendar proposals. Both queries join current membership and active/verified BAM identity in the **same statement** and return no social publishing capability. Their shapes are regression-tested with local SQLite data via a test-only `%s`→`?` placeholder adapter, not a real PostgreSQL connection. The module never executes queries; a future independently authenticated server and DB layer must validate session proof, data types, transaction isolation and performance under real Neon.

## Offline integrity and privacy preflight

`neon_integrity_preflight.py` performs read-only `PRAGMA integrity_check`/`foreign_key_check` and aggregate-only cross-table checks for membership, identities, credentials, sessions, normalized email collisions, role/tokens and held calendar pointers. The strict fixture helper raises on findings but still refuses to declare production readiness. Run it **only on trusted offline synthetic test data** in this phase. It exports no customer rows or secrets, does not connect to Postgres and does not validate production restore, privacy or independent transaction isolation. Some existing offline bootstrapped identities may intentionally have no verified identity record; those conditions appropriately appear as future migration blockers.

## Non-executing priority compare-and-swap SQL preview

`neon_scoped_writes.py` produces a prepared PostgreSQL `UPDATE ... RETURNING` contract for held draft priority only, with a same-statement check of active/verified identity, current eligible team role, tenant and priority-version token. The fixture tests run against SQLite after explicit test-only parameter conversion. No caller can use this module to connect or write to Neon, and it has **no publish/schedule capability**. Before real migration, verify PostgreSQL transaction isolation and rowcount/return values, true authenticated trusted principal resolution, audit events, error mapping and conflict/permission behavior.

## Actual PostgreSQL test container — public GitHub Actions only

The public repository can now run standard GitHub-hosted runners with temporary PostgreSQL 16 in the existing unit-test job. `test_neon_ephemeral_postgres.py` executes the *existing nine-table preview DDL* and tenant-scoped read/priority-CAS SQL against a test-only, loopback PostgreSQL database, including separate simultaneous clients and current membership denial. It refuses unexpected host/database/user settings, uses a run-specific disposable password, drops its test schema, uploads no artifacts, and is skipped without the CI opt-in flag. This is **not** a production Neon connection or BAM PostgreSQL adapter. All other table migrations, production service authentication, durable storage, encrypted backups, and owner approval remain required.

## Five-table collaboration schema extension (ephemeral PostgreSQL CI)

`neon_collaboration_schema.py` adds explicit PostgreSQL DDL for private team invitations, activity audit, role-change audit, review notes and review events. PostgreSQL identity columns replace SQLite AUTOINCREMENT while preserving explicit legacy insert capability (`GENERATED BY DEFAULT AS IDENTITY`). `neon_scoped_collaboration_queries.py` adds an owner-only pending invitation metadata SELECT with current verified identity/member role recheck inside the statement, without selecting bearer token hashes. Synthetic SQLite metadata parity and real temporary GitHub Actions PostgreSQL checks extend the reviewed database subset to **14 tables**. This is a preview, not the actual migrated production schema or a trusted invitation HTTP service.

## Versioned schema replay on disposable CI PostgreSQL

`neon_ephemeral_ci_migrations.py` loads only two fixed known schema stages—nine base tables and five private collaboration tables—under a single PostgreSQL transaction/advisory lock, recording SHA-256 checksums in a disposable CI-only migration journal. Re-execution is a no-op; changed checksums, unknown schema versions and missing tables are denied. It strictly requires loopback `bam_ci_test` PostgreSQL, CI opt-in and a non-production schema. **This is not a deployable production migration runner**, has no data import/export and cannot activate Render, Neon, AI or publishing. Production needs its own reviewed, backup-protected tool, full schema and data migration.

## Third schema stage: provider/AI/identity support metadata

`neon_identity_provider_schema.py` defines a further seven PostgreSQL table previews (total **21**) covering AI mode/memories/request usage, private provider connection vault **references** (not raw OAuth credentials), Google nonce challenges, OAuth attempt PKCE hashes, and attachment metadata. A third CI-only schema migration version replays this stage with journal checksums. `neon_scoped_provider_queries.py` adds current-role tenant-scoped provider metadata reads without selecting a vault ref, and same-identity AI usage queries. Synthetic SQLite and actual temporary PostgreSQL tests confirm isolation and revocation; these are *not* a real OAuth integration, AI billing implementation, content storage provider or Neon deployment.

## Fourth stage: AI cost limits, verified facts and held draft components

`neon_ai_budget_schema.py` adds eight SQL preview tables, bringing the reviewed test subset to **29 tables**. The stage also adds `reserved_micro_usd` and `unpriced_requests` to stage-3 user AI usage, mirroring the actual local sponsorship initializer's post-upgrade columns. Cost ledger schema preserves the tenant/user-scoped unique trusted-usage hash, while stage-only operator control starts `paused=1` rather than silently allowing sponsored provider calls. GitHub Actions uses its disposable PostgreSQL container to verify deduplication and pause rules. Values remain **estimates**, not real provider invoices; no automatic OpenAI permission, production Postgres adapter or approved Neon deployment exists.

## Fifth CI-only PostgreSQL stage: business research and analytic imports

`neon_business_analytics_schema.py` adds seven further Postgres DDL previews: business profiles/topics/sources/competitor blocks, audience observation records, analytics cursors, and legacy tenant ownership metadata. `neon_scoped_business_analytics.py` offers *non-executing* parameterized tenant/current-owner research and synthetic audience read contracts, each joining verified active identity and current membership. Stage 5 of temporary CI-only Postgres now covers **36 tables** and tests cross-business isolation and composite foreign keys. It is not a production database driver, real insights feed, hosted app or scraped source ingestion.

## Sixth disposable CI stage: tenant-owned review and scheduling state

`neon_tenant_content_schema.py` previews four legacy tenant_posts, tenant_approvals, tenant_events and scheduling_settings tables, bringing the reviewed subset to **40 tables**. Explicit tenant/post composite foreign keys keep decisions attached to the correct business, while `neon_scoped_tenant_content.py` builds non-executing, active identity/membership checked review and scheduling read queries. The source `approved` value is an **offline editorial decision**, never a publishing authorization. No actual scheduling dispatcher, social-provider connection or hosted service exists.

## Seventh disposable CI stage: editorial provenance, approved facts and email actions

`neon_review_security_schema.py` adds six source-compatible PostgreSQL DDL previews (46 total) for editorial source/identity attestations, nonpublishing inbox, signed owner approval intents, revoked/expiring TruthGuard facts, creator account screening and hashed email verify/reset purposes. `neon_scoped_review_facts.py` generates a parameterized owner/manager read guarded by active verified member and expiration/revocation constraints. Temporary PostgreSQL tests verify denial of cross-business facts and invalid publish-like statuses; no actual email delivery, provider OAuth, provider posting or customer data migration.

## Query seam: hashed session token to private draft/calendar read

`neon_authenticated_read_contract.py` prepares read-only PostgreSQL SELECTs bound to the **SHA-256 digest of a server-presented session token** rather than trusting caller-supplied subject IDs. It rechecks session validity, expiration, role change, membership and identity verification with tenant and draft scope in a single statement. Local and disposable PostgreSQL tests deny expired/revoked sessions, stale-role and other-business access. The builder never opens a DB or starts an HTTP listener. Production still requires trusted HTTPS/cookie transport, CSRF, origin checks, admission limits, database pooling, encrypted backups and explicit hosting approval.

## Exact next steps before hosted private beta

1. Inventory and explicitly port **all remaining tables** (team invitations, audit, AI preferences, cost ledgers, media metadata, provider connections, consent, pending drafts and revision history). The nine-table preview is incomplete by design.
2. Introduce a separate PostgreSQL data-access implementation with explicit parameterized SQL, strict transaction, connection-pool and retry guarantees. Do not automatically translate arbitrary SQLite queries. Map `BLOB` → `BYTEA`, `AUTOINCREMENT` → generated identity, `PRAGMA` to versioned PostgreSQL migrations, and verify `ON CONFLICT` semantics.
3. Preserve tenant uniqueness and compare-and-swap across independent PostgreSQL connections; audit any `SELECT`-then-`UPDATE` race and revoke stale sessions immediately.
4. Migrate only with user-approved live infrastructure and an encrypted backup, reversible migration version, sandbox verification, row-level parity checks and restore drill. Never include real password hashes, tokens, customer content, database URLs or raw data in GitHub or CI logs.
5. Build a separate audited HTTPS production gateway with durable rate limits and secret vault. All provider publishing and paid AI remain disabled. Non-executable proposals must never become a posting queue by virtue of migration.

## Cost and authorization

Target remains one new separate $7/month **Render Starter** BAM service and one dedicated **Neon Free PostgreSQL** project, *planning only*. Additional service or paid worker/storage/backup/email/AI costs: **$0 authorized**. No resource creation, connection or deployment may happen without new explicit owner approval. See `BAM_HOSTING_PLAN.json` and `PRIVATE_BETA_INFRASTRUCTURE.md`.


## Token-authenticated priority-only edit query (November 12, 2026 candidate)

The non-executing neon_session_write_contract SQL builder hashes the server-presented session token and performs same-statement tenant, role, identity, expiry and revocation checks while comparing a draft priority version token. Offline and ephemeral PostgreSQL tests include cross-business denial, stale edits and concurrent writers. This is not a production database adapter, live gateway, user-facing API or publication permission. Trusted ingress, transaction controls, backups, full schema port and explicit deployment approval remain required.


## All-stage preview inventory (November 12, 2026 candidate)

The local no-data schema inventory now tracks all seven PostgreSQL DDL preview groups (9+5+7+8+7+4+6 = **46 source tables reviewed**), the remaining initialized local tables that do not yet have previews, a per-table review flag, and previewed optional tables absent from a fresh gateway. Legacy nine-table subset fields remain for compatibility. This improves roadmap visibility **without** moving records, connecting to Neon, proving a PostgreSQL production adapter or enabling a live hosted application. Source parity, full migration, transaction semantics, backup/restore and approval are still required.


## Current owner-only invitation SQL security (November 12, 2026 candidate)

A new SQL-only `neon_session_collaboration_contract.py` builds a limited owner-only pending invitation metadata SELECT, deriving the current owner from a verified hashed session token and checking membership, role, identity validity and expiration/revocation in the same SQL statement. This does not expose bearer invite token hashes, issue or send invitations, or add a production PostgreSQL adapter, gateway or deployment. Validate against disposable PostgreSQL and repeat production authentication/transaction testing only after explicit separate deployment approval.


## First executable disposable-only PostgreSQL session facade (November 12, 2026 candidate)

`neon_ci_session_adapter.EphemeralSessionPostgres` consumes an *already-created* psycopg connection restricted to the known GitHub CI PostgreSQL loopback database/schema/user. It executes session-hash-authenticated held draft/calendar read, owner invitation metadata read and atomic priority CAS using existing audited SQL contracts. Synthetic real-PostgreSQL integration tests check cross-tenant denial, stale writes and cross-connection session revocation. It deliberately refuses production databases, Neon and arbitrary TCP hosts; it cannot open a new connection, accept web traffic, publish or schedule. Next engineering gates remain an independent production adapter/pool, atomic transaction design, full table port, actual data migration/restore tests and explicitly authorized secure hosting.
