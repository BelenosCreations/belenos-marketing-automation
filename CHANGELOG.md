# Changelog

## Verification workflow update — 2026-11-10

- Added Python compile-all validation before GitHub Actions unit-test discovery.
- CI pass status for the current development branch remains unconfirmed.


## Held-draft lifecycle controls — 2026-11-10 (development branch)

### Added
- Authenticated hold-state API and local terminal controls for postponing, marking unavailable, and reopening incomplete drafts.
- Regression tests for hold/reopen lifecycle, cross-tenant access denial, viewer permissions and strict request validation.

### Fixed
- Return a not-found HTTP response instead of an unhandled exception when a draft ID does not exist in the active business.

### Limitations
- Local prototype only; no upload, AI generation, scheduling or publishing.


## Local held-draft workflow integration — 2026-11-10 (development branch)

### Added
- Tenant-scoped held Content Requests and missing-content suggestions in the account dashboard and terminal demo.
- Authenticated HTTP creation of manually entered held drafts, with strict request validation and server-derived tenant.
- Demo drafts for each example business and interactive terminal draft creation.
- HTTP integration regression cases for draft creation, tenant isolation and rejection of client-supplied business IDs.

### Limitations
- No AI draft generation, actual media upload, public server, production authentication, social OAuth or publishing. Current branch test run not independently verified.


## Cross-workflow authorization hardening — 2026-11-10 (development branch)

### Fixed
- Require current session role in Content Request and owner approval-intent operations.
- Reject stale sessions following role upgrades, not only downgrades.
- Update Content Request test fixture to use verified attachment IDs instead of unsupported content references.

### Added
- Regression tests for stale role promotion into content creation and owner approval.


## Local account workflow prototype — 2026-11-10 (development branch)

### Added
- Loopback-only development HTTP gateway with BAM account overview, business activation, logout, and identity-wide logout routes.
- Runnable disposable demo server and interactive terminal client for switching between sample businesses.
- End-to-end HTTP integration tests using real BAM session, membership, connection registry and dashboard services.
- Authenticated self-service logout everywhere, revoking sessions across businesses without affecting other users.
- Transport regression cases covering malformed input, cross-origin requests and DNS rebinding attempts.

### Fixed
- Revoke newly issued session when dashboard activation fails after business switching.

### Limitations
- Offline local-only development demo, not a production HTTP service or Android UI. Tests committed but passing CI not independently confirmed. No social OAuth or publishing.


## Account read API boundary — 2026-11-10 (development branch)

### Added
- Transport-neutral read-only BAM account adapter for overview, authorized business activation and current-session logout.
- Six additional regression cases for tenant isolation, role-scoped switching, logout and invalid requests.

### Limitations
- No HTTP server, deployed authentication, live OAuth or publishing. CI results not independently verified in this session.


## Account dashboard integration — 2026-11-10 (development branch)

### Added
- Read-only, role-aware account dashboard composed from BAM sessions, business switching and social account directory.
- Five focused regression cases for tenant visibility, permission filtering, switching, session revocation and stale roles.

### Fixed
- Business selection now requires a current-role session; a role change invalidates stale source sessions before switching.

### Limitations
- No deployed API or mobile UI; tests committed but not independently executed. Live provider connections and publishing remain disabled.


## Phase 8.9 — 2026-11-10 (development branch)

### Added
- Fresh membership and role validation for privileged BAM session resolution.
- Identity-wide session revocation across businesses for trusted administrative flows.
- Stronger session checks in business switching and social connection directory.
- Three additional regression cases for role freshness, inactive memberships and global sign-out.

### Limitations
- Offline security primitives only; no live identity provider, mobile token vault or publishing.


## Phase 8.8 — 2026-11-10 (development branch)

### Added
- Target-business session issuance in existing business selector, using current tenant membership and role.
- Revalidation of source-business membership before business listing and switching.
- Three additional regression cases for activation, unauthorized targets and revoked source access.

### Limitations
- Production identity verification, mobile account switch UI and provider integrations remain outstanding. Publishing disabled.


## Phase 8.7 — 2026-11-10 (development branch)

### Added
- Read-only multi-platform social connection directory behind BAM session and tenant-scoped analytics permissions.
- Seven regression cases for independent business/platform listings, role checks, session expiry and metadata privacy.

### Architecture
- BAM authentication remains independent from optional social platform account connections.

### Limitations
- No live provider OAuth, global BAM account-switching interface, production identity verification or publishing.


## Phase 8.6 — 2026-11-10 (development branch)

### Added
- Backend-only OAuth attempt state ledger with PKCE S256 challenge and bounded expiry.
- Single-use, tenant/provider/account-bound callback state validation with transactional replay prevention.
- Ten regression cases for replay, scope, expiry, verifier and stored-hash behavior.

### Limitations
- No OAuth redirect handling, token exchange, vault, session binding, live provider connection or publishing.


## Phase 8.5 — 2026-11-10 (development branch)

### Added
- Fail-closed provider connection gate before analytics preview and import.
- Rejection of unconnected, expired, refresh-required and revoked connections before fetching.
- Eight regression cases for connected access, invalid connection states and tenant/caller isolation.

### Limitations
- The underlying adapter is internal and can be called directly unless a production server enforces the gated interface. No OAuth or live provider integration.


## Phase 8.4 — 2026-11-10 (development branch)

### Added
- Offline per-tenant/provider/account connection metadata registry with secret-vault references, scope and lifecycle states.
- Expiry-aware status responses that do not expose vault references.
- Nine regression cases for lifecycle, isolation, read-only scopes and validation.

### Limitations
- No OAuth, real secret vault, token refresh, provider verification or live connection.


## Phase 8.3 — 2026-11-10 (development branch)

### Added
- Authorized read-only synchronization health assessment with missing/current/stale/invalid checkpoint states.
- Configurable freshness threshold and nonexecuting recovery guidance.
- Eight regression cases for health states, isolation and validation.

### Limitations
- No real provider authentication, automatic retries, network requests or publishing.


## Phase 8.2 — 2026-11-10 (development branch)

### Added
- Provider-neutral, offline analytics page adapter with pre-fetch account authorization and checkpoint-aware import.
- Business-local weekday/hour bucketing of historical publication times.
- Seven regression cases for authorization, validation, preview and import.

### Limitations
- The injected fetcher is not a live provider connector; no OAuth, live data access, scheduling or publishing.


## Phase 8.1 — 2026-11-10 (development branch)

### Added
- Offline tenant/platform/account synchronization checkpoints with exact expected-cursor validation.
- Bounded atomic batch imports, preserving checkpoint and observation rollback together.
- Seven regression cases for credentials, stale cursors, duplicate imports and partial rollback.

### Changed
- Import boundary exposes reusable credential authorization; observation insertion preserves caller-owned transactions.

### Limitations
- No live provider synchronization, OAuth, background jobs or publishing.


## Phase 8.0 — 2026-11-10 (development branch)

### Added
- Tenant/platform/account-bound offline analytics import interface using server-injected credentials.
- Validation and normalization of integer engagement and impression counts, with duplicate post protection through the observation store.
- Nine regression cases for authentication, isolation, malformed metrics and duplicate ingestion.

### Limitations
- Caller authentication is not provider-origin verification; no OAuth, external API synchronization or publishing.


## Phase 7.9 — 2026-11-10 (development branch)

### Added
- Offline SQLite engagement observation store keyed by tenant, platform and source post ID.
- Bounded time-window and candidate queries with tenant/platform filtering.
- Seven regression cases for deduplication, scope isolation, validation and ranker integration.

### Limitations
- Ingestion is not authenticated against a social provider and is not a live analytics connection. No scheduling or publishing.


## Phase 7.8 — 2026-11-10 (development branch)

### Added
- Offline tenant-scoped candidate ranking using supplied observed engagement rates and minimum sample thresholds.
- Optional smart-preview integration with explicit insufficient-data fallback; manual selection remains independent.
- Seven regression cases for ranking, malformed/cross-tenant data and nonpublishing previews.

### Limitations
- No connected analytics ingestion, statistical confidence adjustment, prediction or publishing.


## Phase 7.7 — 2026-11-10 (development branch)

### Added
- Timezone-aware, read-only manual/smart scheduling preview tied to the held readiness assessment.
- Validation of daylight-saving gaps/overlaps, duplicate candidates, mode mismatch and tenant isolation.
- Eight regression cases for preview boundaries.

### Limitations
- Smart mode uses earliest-candidate demonstration only; no engagement optimization, job creation or publishing.


## Phase 7.6 — 2026-11-10 (development branch)

### Added
- Read-only schedule-readiness assessment with explicit safety blockers and owner/tenant authorization inherited from the intent ledger.
- Seven regression tests for held scheduling, revoked intent, stale content, unverified media, invalid time and tenant isolation.

### Limitations
- All proposed schedules remain held; final approval and publishing integrations are not implemented.


## Phase 7.5 — 2026-11-10 (development branch)

### Security
- Validate all required supporting attachments against the tenant/request/item-scoped verified registry before recording intent.
- Revalidate attachments when inspecting previously recorded intent; expose `attachments_verified`.
- Replace fake attachment fixtures with registered verified attachments; add three negative regression cases.

### Limitations
- The offline attachment registry does not inspect file bytes or grant publishing permissions.


## Phase 7.4 — 2026-11-10 (development branch)

### Added
- Approval-intent snapshot digest of channel, required items and supplied content references.
- Inspection flag `content_unchanged`; changed supporting content requires new review.
- Schema migration for existing intent tables, with missing historical digests treated as stale.
- Three regression cases for replacement, unchanged content and legacy records.

### Limitations
- Metadata fingerprinting does not independently verify underlying media or grant publishing rights.


## Phase 7.3 — 2026-11-10 (development branch)

### Changed
- Approval-intent inspection now rechecks current Content Request readiness, not just draft text.
- Adds `content_complete` and `requires_new_review` status indicators.
- Regression case for a previously completed request later placed on hold.

### Safety
- Approval intent remains nonpublishing and does not grant scheduling access.


## Phase 7.2 — 2026-11-10 (development branch)

### Added
- Owner-authenticated, tenant-scoped approval-intent recording bound to a complete Content Request and exact review receipt.
- Revocation and read-only current-draft integrity inspection.
- Five regression tests for authorization, completeness and revocation.

### Limitations
- Intent is not final approval and cannot schedule or publish content.


## Phase 7.1 — 2026-11-10 (development branch)

### Added
- Draft-bound, deterministic TruthGuard review receipt and stale/tampered report validation.
- Eight regression cases covering integrity, cross-tenant/request mismatch and held-only receipts.

### Limitations
- SHA-256 receipts are not signed authorization; production audit storage and separate approvals are future work.
- No publishing or scheduling capability is enabled by receipts.


## Phase 7.0 — 2026-11-10 (development branch)

### Added
- Correlation of heuristic risk signals with exact stored-draft annotation spans.
- Read-only `uncovered_risk_signals` and `risk_signals_annotated` review indicators.
- Two regression cases; annotation never authorizes publication.


## Phase 6.9 — 2026-11-10 (development branch)

### Security
- Reject facts whose approval timestamp is later than the requested review time.
- Add five regression cases for temporal and tenant boundaries.
- Preserve held review status and disabled publishing.


## Phase 6.8 — 2026-11-10 (development branch)

### Security hardening
- Validate bounded, correctly typed TruthGuard claim lists before hash-based draft span matching.
- Add malformed and oversized claim regression coverage.
- Retain fail-closed held status and disabled publishing.


## Phase 6.7 — 2026-11-10 (development branch)

### Added
- Heuristic source-span signals for pricing/discounts, guarantees, urgency/availability, business hours and testimonials.
- Risk signals integrated into authenticated, read-only TruthGuard Content Request review.
- Ten regression tests committed.

### Limitations
- Pattern matching is incomplete and cannot establish factual correctness or publication eligibility.
- Current-branch tests have not yet been independently executed; publishing disabled.


## Phase 6.6 — 2026-11-10 (development branch)

### Changed
- TruthGuard review now cross-checks supplied verified claims against exact source-span annotations in the stored draft.
- Exposes detached claims separately from knowledge-base verification, avoiding false draft-grounding impressions.
- Three regression tests committed.

### Limitations
- Does not independently extract every factual claim; all drafts remain held and publishing disabled.
- Full current-branch test execution still unverified.


## Phase 6.5 — 2026-11-10 (development branch)

### Added
- Exact source-span audit for TruthGuard claim annotations, with overlap/mismatch detection, unannotated-text visibility and draft fingerprint.
- Audit included in authenticated read-only Content Request review results.
- Ten audit tests and two integration tests committed.

### Limitations
- Source-span integrity does not prove factual completeness or truth. No publish eligibility is granted.
- Current-branch test execution not yet confirmed; publishing disabled.


## Phase 6.4 — 2026-11-10 (development branch)

### Added
- Authenticated read-only TruthGuard review for stored business content requests.
- Claim evidence and content-completeness reporting without approval or publishing side effects.
- Seven regression tests.

### Limitations
- Claim lists are supplied by the caller and are not guaranteed complete; all drafts remain held.
- Tests committed but not independently executed.


## Phase 6.3 — 2026-11-10 (development branch)

### Added
- Authenticated owner-only TruthGuard fact approval, lookup and revocation service.
- Fresh membership, tenant and session checks; eight regression tests.

### Limitations
- Owner confirmation is not independent external verification; no production API, Android UI or publish gate.
- Tests committed but execution unverified.


## Phase 6.2 — 2026-11-10 (development branch)

### Added
- TruthGuard approved fact registry with tenant isolation, provenance, expiration and revocation.
- Exact normalized claim verification against current approved facts and evidence references.
- Fail-closed full-draft review; twelve regression tests.

### Limitations
- No authenticated fact administration, independent source verification, complete claim extraction or production publishing gate.
- Tests committed but not independently executed; publishing remains disabled.


## Verification checkpoint — 2026-11-10

### Verified
- Executed the archived Phase 3.2 offline Python unit tests: 26 passed, 0 failed, 0 errors.
- Recorded test command, verification scope and release gates in VERIFICATION.md.

### Still unverified
- Newer GitHub development modules through Phase 6.1; no passing current-branch CI run confirmed.
- Live integration, Android UI and publishing remain disabled/not implemented.


## Phase 6.1 — 2026-11-10 (development branch)

### Added
- Read-only multi-post schedule preview from authenticated per-business Manual/Smart settings.
- Distinct proposed slots, held-draft visibility and settings revision metadata.
- Six regression tests.

### Limitations
- Preview readiness flags are caller-provided; they are not trusted for actual publishing.
- No scheduling jobs, Android UI, HTTP API or publishing. Tests not independently executed.


## Phase 6.0 — 2026-11-10 (development branch)

### Added
- Strict Manual/Smart scheduling settings screen data contract.
- Validated mode switching, exact weekly time editing and revision metadata.
- Seven tests for data roundtrip, access restrictions and stale updates.

### Limitations
- No rendered Android screen or HTTP API; publishing disabled.
- Test execution unverified.


## Phase 5.9 — 2026-11-10 (development branch)

### Added
- Authenticated business-specific saved scheduling settings wired to the posting-time proposal engine.
- Explicit not-configured response, revision metadata and nonpublishing result flags.
- Seven integration regression tests.

### Limitations
- No actual scheduling jobs, publishing or Android UI.
- Test execution unverified.


## Phase 5.8 — 2026-11-10 (development branch)

### Added
- Session-authenticated Manual/Smart scheduling settings service.
- Fresh tenant membership validation and revision-aware edits.
- Seven security and persistence regression tests.

### Limitations
- No network endpoint, Android screen, scheduler or publishing.
- Test execution unverified.


## Phase 5.7 — 2026-11-10 (development branch)

### Added
- Persistent tenant-scoped Manual/Smart scheduling settings, timezone, weekly times and smart-hour preferences.
- Fresh business membership checks and revision-based edit conflict protection.
- Nine regression tests for persistence, permissions and isolation.

### Limitations
- Internal offline repository only; no HTTP or Android settings screen, no publishing.
- Tests committed; execution unverified.


## Phase 5.6 — 2026-11-10 (development branch)

### Added
- Manual weekly posting times per business timezone, preserving exact user-selected minutes.
- Smart posting-time suggestions based on post subject, audience, preferred hours and supplied engagement observations.
- Explicit per-post time overrides in either mode.
- Mandatory hold for missing content or approval; suggestions never auto-publish.
- Twelve scheduling-policy regression tests.

### Limitations
- Offline policy engine only; no saved user settings, platform analytics, Android scheduling UI or publishing integration.
- Tests committed, execution unverified.


## Phase 5.5 — 2026-11-10 (development branch)

### Added
- Offline SHA-256 byte comparison, size enforcement and basic file signature checks for attachments.
- Tenant-scoped pending-record inspection that never grants verification or publishing permission.
- Ten regression tests for byte validation, signatures, hash mismatch and access boundaries.

### Limitations
- No storage integration, malware scanner, full media decoding or consent validation.
- Tests committed but execution remains unverified; publishing disabled.


## Phase 5.4 — 2026-11-10 (development branch)

### Added
- Authenticated upload preflight for active business-specific content requests.
- File-type allowlist and size limits; server-generated private storage identifiers.
- Pending-only attachment registration with no upload URL or publish capability.
- Ten regression tests for authorization, limits and session handling.

### Test status and limitations
- Tests committed; execution unverified.
- No actual byte transfer, object storage, scanning, hash verification or Android UI.
- Publishing remains disabled.


## Phase 5.3 — 2026-11-10 (development branch)

### Added
- Authenticated, read-only Content Requests dashboard projection with business-specific counts and cards.
- Per-draft missing/supplied content checklist, prepared text, capture suggestions and priority.
- Explicit non-publishable and non-schedulable flags.
- Five tests covering partial completion, tenant isolation, revoked sessions and hold states.

### Test status and limitations
- Tests committed; not independently executed.
- No rendered Android screen, live upload, trusted scanner or publishing integration.


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
