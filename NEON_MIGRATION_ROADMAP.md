# BAM SQLite → Neon PostgreSQL transition (offline preparation)

**Status: only partial schema blueprint, NO migration, NO Neon connection, no approved deployment.**

BAM's current alpha instantiates multiple SQLite-first service modules with `CREATE TABLE` statements, `PRAGMA table_info` checks and occasional SQLite-specific `AUTOINCREMENT`, `BEGIN IMMEDIATE` and `sqlite3.IntegrityError` handling. Passing unit tests in SQLite does not prove code will run on PostgreSQL. Never expose the offline gateway to Render or insert a PostgreSQL URL into its SQLite connection.

## Verified offline subset blueprint

`neon_schema_blueprint.py` contains **DDL preview only**, with no driver, network, credentials or execution switch, for nine of the existing alpha tables: identities, password credentials, Google identities, membership, sessions, account login failure tracking, held content requests, posting preferences and non-executable calendar proposals. It preserves the text/token hash and legacy JSON-string data representation for test parity; `BYTEA` replaces SQLite password digest/salt BLOB. `inspect_sqlite_subset` checks the live local schema's column names and publishes only table counts, schema digest and permanent readiness blockers, never credentials, user data or drafts. These are the **first nine tables of a larger schema**, not a deployable migration.

## Exact next steps before hosted private beta

1. Inventory and explicitly port **all remaining tables** (team invitations, audit, AI preferences, cost ledgers, media metadata, provider connections, consent, pending drafts and revision history). The nine-table preview is incomplete by design.
2. Introduce a separate PostgreSQL data-access implementation with explicit parameterized SQL, strict transaction, connection-pool and retry guarantees. Do not automatically translate arbitrary SQLite queries. Map `BLOB` → `BYTEA`, `AUTOINCREMENT` → generated identity, `PRAGMA` to versioned PostgreSQL migrations, and verify `ON CONFLICT` semantics.
3. Preserve tenant uniqueness and compare-and-swap across independent PostgreSQL connections; audit any `SELECT`-then-`UPDATE` race and revoke stale sessions immediately.
4. Migrate only with user-approved live infrastructure and an encrypted backup, reversible migration version, sandbox verification, row-level parity checks and restore drill. Never include real password hashes, tokens, customer content, database URLs or raw data in GitHub or CI logs.
5. Build a separate audited HTTPS production gateway with durable rate limits and secret vault. All provider publishing and paid AI remain disabled. Non-executable proposals must never become a posting queue by virtue of migration.

## Cost and authorization

Target remains one new separate $7/month **Render Starter** BAM service and one dedicated **Neon Free PostgreSQL** project, *planning only*. Additional service or paid worker/storage/backup/email/AI costs: **$0 authorized**. No resource creation, connection or deployment may happen without new explicit owner approval. See `BAM_HOSTING_PLAN.json` and `PRIVATE_BETA_INFRASTRUCTURE.md`.
