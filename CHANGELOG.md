# Changelog

## Phase 4.1 — 2026-11-10 (development branch)

### Added
- Authenticated, read-only business switcher with per-business role resolution.
- Eight account-switching tests covering separate business access and deactivation.

### Test status
- Test definitions committed; GitHub workflow run not returned for latest commit, so execution remains unverified.

### Known limitations
- Login identity verification and Android business-switching UI are not implemented.
- Trusted server must derive creator screening outcomes; callers must not be allowed to mark competitors cleared.
- Competitor host blocklist is conservative and needs profile-level social account identifiers to avoid broad shared-domain blocks.
- Publishing disabled.


## Phase 4.0 — 2026-11-10 (development branch)

### Added
- General-purpose per-business industry/topic/source curation, independent across business tenants.
- Local competitor blocklist by business and conservative review for unknown or possible local competitors.
- Business-specific curation and competitor regression tests.

### Test status
- Tests committed; full suite and CI results not yet verified.

### Known limitations
- Competitor detection is not automated: trusted configuration and human screening are required. Domain blocking alone cannot identify all competitors, social profiles, syndicated content, or mirrors.
- Business profiles and source settings lack authenticated owner-facing API; no automatic sharing enabled.
- Publishing remains disabled.


## Phase 3.9 — 2026-11-10 (draft PR #1)

### Added
- Owner-authorized, one-use, expiring, revocable employee invitation tokens (hashes stored at rest).
- 12 invitation lifecycle tests; 98 tests defined across repository.
- Draft pull request #1 for code review and CI without merging to main.

### Test status
- GitHub Actions run not yet visible for the draft PR; new tests unverified.

### Known limitations
- Invitation redemption requires externally authenticated verified subject identity; no authentication provider implemented.
- Invitation delivery, rate limits, audit and transactional concurrency hardening remain.
- Production exposure of legacy workflow prohibited; publishing disabled.


## Phase 3.8 — 2026-11-10 (development branch)

### Added
- Native tenant-keyed post, approval and event tables in `tenant_content.py`.
- Session and current-role authorized `TenantApprovalService` for native tenant records.
- 12 new isolation and permission tests; 86 tests defined across repository.

### Test status
- Commits completed; GitHub combined status returned no checks. Tests not independently verified.

### Known limitations
- Legacy workflow remains separately available and must not be exposed as production API.
- Native storage is an independent development path, not yet a migration of legacy records.
- Trusted ingestion, classification and user authentication are not production-ready.
- No API, Android client, or live publishing; publishing disabled.


## Phase 3.7 — 2026-11-10 (development branch)

### Added
- Immutable tenant ownership registry for offline posts and discovered events.
- Fail-closed ownership checks before approval and event confirmation.
- Four ownership regression tests; prior approval tests updated to register ownership.

### Test status
- Changes committed; test execution and CI results not yet verified.

### Known limitations
- Ownership is a transitional side table rather than native tenant columns and tenant-filtered queries.
- Registration is trusted-server-only and must never accept unverified client ownership claims.
- Existing workflow functions can bypass the gateway; no production API exposure is safe yet.
- Publishing remains disabled.


## Phase 3.6 — 2026-11-10 (development branch)

### Added
- Offline approval gateway combining session validity and current membership authorization.
- Owner-only promotional/event approvals and revocations; manager routine approvals.
- 12 security-focused unit tests committed.

### Test status
- New tests committed; full suite execution and GitHub Actions status not yet verified.

### Known limitations
- Legacy posts and events are not tenant-scoped in the database: **do not expose gateway through an API** until tenant isolation is added to these records and queries.
- Session issuance still depends on an external authenticated identity provider that is not implemented.
- Legacy workflow functions remain callable internally without the gateway; production must restrict access through trusted services.
- Publishing remains disabled.


## Phase 3.5 — 2026-11-10 (development branch)

### Added
- Offline tenant-scoped account directory and one-time owner bootstrap.
- Owner-managed employee role assignment and deactivation.
- Authorization against current directory membership rather than stale role claims in sessions.
- 10 account-directory unit tests.

### Test status
- Changes committed to development branch; CI and local test results not yet verified.

### Known limitations
- No authenticated login, secure invitation workflow, API middleware, or Android client.
- Bootstrap must be restricted to trusted server setup in production.
- Production implementation must use transactional database operations and enforce last-owner safeguards.
- Publishing remains disabled.


## Phase 3.4 — 2026-11-10 (session prototype)

### Added
- SQLite-backed opaque session tokens with SHA-256 token hashes at rest.
- Server-side expiry, single-session revocation, and tenant-scoped user-wide revocation.
- 10 unit tests for issuance, expiry, revocation, and invalid inputs.

### Test status
- Tests committed; local execution and GitHub Actions results not yet verified.

### Known limitations
- No real login, identity provider, password handling, biometric implementation, API authorization middleware, or employee directory.
- Sessions currently capture a role at issuance; a production API must recheck current user/tenant membership and permissions on each request, or revoke sessions on role changes.
- SQLite prototype is not configured for production cloud hosting. Publishing remains disabled.


## Phase 3.3 — 2026-11-10 (authorization foundation)

### Added
- Fail-closed, tenant-scoped role authorization policy for owner and future staff.
- 12 offline tests for role boundaries, tenant isolation, inactive identities, and privileged actions.

### Test status
- New tests committed; GitHub Actions result not yet verified.

### Known limitations
- Policy only: no authentication provider, token verification, user database, Android app, or API middleware yet.
- Existing prototype approval workflow is not yet wired to this policy.
- No live publishing or scheduling; publishing remains disabled.


## Phase 3.2 — 2026-11-10 (offline prototype imported to GitHub)

### Added
- Imported the offline policy engine, approval/audit workflow, and engagement optimizer.
- Imported 26 unit tests covering staging, approvals, dry runs, curation, and time ranking.
- Added GitHub Actions unit-test workflow and Python/credential-safe .gitignore.
- Created project documentation and version history.

### Test status
- All 26 tests passed locally against the original Phase 3.2 ZIP before import.
- GitHub Actions workflow is configured; remote run status has not yet been verified.

### Known limitations
- No authenticated approval service or real creator discovery.
- Trust and fact-verification flags are caller-supplied in the prototype.
- Content classification trusts caller-provided category; promotion authorization uses naive text matching.
- No live Metricool scheduling or Facebook publishing.
- Publishing remains disabled.

## Phase 3 — 2026-11-10 (offline prototype)
- Draft staging, authorization, audit, approval and dry-run workflow.
- Local test suite, with no network or publishing implementation.
