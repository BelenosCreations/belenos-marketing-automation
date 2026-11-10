# Changelog

## Phase 5.2 — 2026-11-10 (development branch)

### Added
- Tenant-scoped attachment metadata and pending/verified/rejected lifecycle.
- Authenticated Content Request completion now requires a matching verified attachment ID, rather than an arbitrary user-supplied reference.
- Ten attachment tests and two additional authenticated service tests.

### Limitations and test status
- No actual file uploader, scanning worker, consent verification or private object storage integration.
- Tests committed; execution and CI status remain unverified.
- Publishing disabled.


## Phase 5.1 — 2026-11-10 (development branch)

### Added
- Authenticated Content Request application service with fresh per-operation membership and role checks.
- Session revocation, expiry, cross-business access, role downgrade and viewer-read-only test cases (14 tests).
- Content completion continues to mean ready for review, never scheduled or published.

### Test status and limitations
- Tests committed; execution and CI results not independently verified.
- Internal offline service only; trusted asset validation, external login and HTTP endpoints remain future work.


## Phase 5.0 — 2026-11-10 (development branch)

### Added
- Tenant-isolated Content Requests storage for prepared drafts that need user photos, videos, details or permissions.
- Per-draft suggestions, required-item checklists, priority, content references and hold states.
- Transition to ready-for-review only after all requested references are supplied; never auto-publish.
- Nine regression tests for partial completion, cross-tenant isolation, postponement and validation.

### Test status and limitations
- Tests committed, execution not independently verified.
- Content reference presence is not yet proof of actual upload or permission; trusted backend validation remains required.
- No mobile UI, authenticated API, scheduling or publishing in this phase.


## Phase 4.9 — 2026-11-10 (development branch)

### Security and integrity
- Persisted editorial candidate SHA-256 digests and added migration for existing review queues.
- Rechecks reject modified source, summary, verification, and safety metadata; legacy undigested rows fail closed until re-intake.
- Capped server attestations at 24 hours and added expiry-limit test coverage.
- Corrected an intake test expectation for unverified creators held in review.

### Test status and limits
- Regression tests committed; execution not independently verified.
- No external verification worker, Android release, or publishing integration.


## Phase 4.8 — 2026-11-10 (development branch)

### Added
- Authenticated editorial intake facade that reads server-side creator attestations instead of client clearance flags.
- Business-role authorization, expired-attestation hold, and competitor re-screening safeguards.
- Ten intake regression tests.

### Test status
- Committed, not yet independently executed or confirmed by CI.

### Limitations
- No real external identity verification worker, public API, Android client or publishing integration.
- Legacy direct inbox entry points remain internal-only; production must not expose them.
- Publishing disabled.


## Product naming decision — 2026-11-10

- Adopted **BAM — Belenos Automatic Marketing** as the official product and future Android app name.
- Clarified that Belenos is the software brand, not an industry or customer limitation.
- Updated the development README while retaining the existing GitHub repository path and history.
- Working tagline: *Your marketing. On autopilot.* Trademark and app-store name availability have not been checked.
- No code, app package identifier, GitHub repository name, or production publishing settings changed.


## Product scope clarification — 2026-11-10

- Clarified that the platform is industry-agnostic and multi-tenant, intended for businesses beyond the initial pilots.
- Identified Belenos Creations and Busy B Cleaning Service as examples, not hard-coded tenants or target-market limits.
- Updated README product goals to use business-neutral language.
- Documentation-only change; publishing remains disabled.


## Phase 4.7 — 2026-11-10 (development branch)

### Added
- Expiring, business-scoped server attestation registry for creator identity and competitor screening.
- Editorial review facade now rejects client-supplied identity/competitor clearance and reads fresh server attestations.
- Eight new attestation tests and two new review-facade regression tests.

### Test status
- Test definitions committed; execution remains unverified.

### Known limitations
- Attestation creation is a trusted internal operation; external verification worker and authorization-gated API are not yet implemented.
- Recheck grants human-review eligibility only, never scheduling or publishing.
- No Android application or live publishing integration.


## Phase 4.6 — 2026-11-10 (development branch)

### Added
- Authenticated editorial review facade requiring an active owner or marketing-manager membership.
- Fresh creator/source/competitor recheck before human review, with no scheduling or publishing action.
- Ten role, revocation, cross-tenant and policy-change tests.

### Test status
- Code and tests committed; full test execution not verified. GitHub Actions push and pull-request triggers exist but successful runs have not been confirmed.

### Known limitations
- The facade accepts identity verification and competitor clearance from its caller: production must derive these solely from a trusted resolver, never mobile/client parameters.
- No authenticated HTTP endpoint, Android UI, scheduling authorization, or publishing integration yet.
- Publishing disabled.


## Phase 4.5 — 2026-11-10 (development branch)

### Added
- Fresh policy re-evaluation before a queued link can be considered for editorial review; blocked creators are removed.
- Business-neutral curation categories, including facility care and case studies.
- Guard against accidental whole-platform competitor blocks on common social domains.
- Eleven additional regression tests covering rechecks, commercial cleaning and shared social platforms.

### Test status
- Code and test definitions committed; full suite execution and GitHub CI status not yet verified.

### Known limitations
- Review check is not yet bound to an authenticated API, approval, scheduler or publication transaction.
- Trusted identity verification and competitor clearance remain external dependencies.
- Existing queue records are not automatically swept when policies change; review check must be called on use.
- No live discovery or publishing enabled.


## Phase 4.4 — 2026-11-10 (development branch)

### Added
- Tenant-specific editorial inbox for discovered third-party links.
- Combined recommendation gate applied before queuing; review required even for eligible sources.
- Duplicate-link handling and blocked-source re-screen removal.
- Nine new offline tests for review, isolation, duplicate and blocked content.

### Test status
- Code and tests committed; execution and CI status not verified.

### Known limitations
- Inbox reads do not automatically re-screen after policy changes; trusted production review must re-evaluate on every approval or scheduling action.
- Discovery ingestion is offline only; no external source crawler or platform API integration.
- No Android UI, authenticated production API, or publishing activation.


## Phase 4.3 — 2026-11-10 (development branch)

### Added
- Combined recommendation gate requiring both approved business-specific source and verified creator identity.
- Unknown/possible local competitors remain held, known competitors blocked.
- Ten integration tests for topic, tenant, source, creator and competitor controls.

### Test status
- New test definitions committed; execution not yet independently verified.

### Known limitations
- Trusted identity verification and competitor clearance are not implemented.
- The recommendation gate is not connected to ingestion, scheduled jobs, or publishing.
- No Android APK, authenticated public API, or live posting.
- Publishing remains disabled.


## Phase 4.2 — 2026-11-10 (development branch)

### Added
- Business-scoped verified creator identity policy keyed by platform and account ID.
- Explicit blocked, review and approved states, with unknown identities held.
- 12 additional identity policy regression tests.

### Test status
- Tests committed but not independently executed; remote GitHub Actions results still unverified.

### Known limitations
- Creator identity verification is not implemented; trusted external verification must supply it.
- Legacy URL/host-based curation is still separate; production must combine both checks before recommending content.
- Approved creator identity does not authorize publishing, reposting, or use of copyrighted media.
- Publishing remains disabled.


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
