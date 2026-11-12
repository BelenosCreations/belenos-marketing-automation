# BAM Alpha → Private Beta Readiness Gate

**Status as of November 12, 2026:** Private, offline **alpha**. This checklist is an acceptance gate, not a claim that release milestones were reached. BAM remains unpublished and has no permission to call social publishing services or paid AI.

## A. Checks that can be developed without production authorization

| Acceptance gate | Current status | Evidence required before marking complete |
| --- | --- | --- |
| Tenant content and manual schedule PostgreSQL parity | **Four source-compatible test schema tables, stage six, pending CI** | End-to-end authenticated production content/review state and durable scheduler must be separately built and approved before any real publication |
| Business research/analytics PostgreSQL parity | **Stage 5 with seven additional DDL previews, pending CI** | Need a production data adapter, real authorized analytics, tenant-scoped writes and backups; CI tests use synthetic local PostgreSQL only |
| Current incremental cost cap and deployment policy | **$0 new costs authorized; paid Render Starter deferred, neither free Render nor free Neon provisioned** | Continue free CI/offline. Before *any* provider provisioning or new cost, explicitly approve actual scope, quotas, overage safeguards and isolation. A functioning app or unavoidable blocker only triggers reconsideration |
| AI budget and cost accounting PostgreSQL parity | **Eight more DDL previews + usage columns and paused-on test schema, pending CI** | Real billing/model pricing and transactional budget admissions must be independently verified before *separate* approval of paid AI |
| AI/provider/auth metadata PostgreSQL parity | **Seven additional DDL previews, version 3 in ephemeral CI, pending CI** | Full vault lifecycle, actual provider OAuth, real hosted identity and all remaining table migrations are still unimplemented |
| Versioned PostgreSQL schema migrations (CI only) | **Two transactional CI schema stages with checksum journal and drift/idempotency tests, pending CI** | Need independently reviewed production migration runner, full table set, encrypted backup/restore, failure recovery and authorized Neon staging |
| Collaboration and invite PostgreSQL table parity | **Five new DDL previews/owner-only read tests; pending CI** | Full invite transaction semantics, cryptographic token lifecycle and all remaining tables must pass actual Neon staging tests before private beta |
| Real PostgreSQL query/DDL verification on public GitHub CI | **New ephemeral PostgreSQL 16 CI integration candidate, not Neon staging** | Verify actual PG isolation and versioned writes under CI, then port all remaining tables, run real hosted multi-user tests, encrypted backup/restore and explicitly authorized deployment |
| Postgres write-path CAS preview | **Offline contract/SQLite tests passed PR #33 and merged-main CI 43218122644; not exercised on PostgreSQL** | Test same SQL with real Postgres transactions and authenticated server sessions before any hosted edit endpoint; no executable posts |
| Local migration integrity preflight | **Offline preflight passed PR #32 and merged-main CI 43217385358; not a hosted restore test** | Must pass on an approved staging migration from encrypted backup and then real Neon referential/transaction tests; no user data migrated |
| Postgres tenant read-query seam | **Offline query-shape tests passed PR #31 and merged-main CI 43216601082; not actual Neon** | Requires independently authenticated production caller and real Neon transaction/tenant isolation tests; no actual Postgres connection verified |
| Complete local table portability inventory | **Offline full-schema inventory passed PR #31 and merged-main CI 43216601082; port remains incomplete** | Manual PostgreSQL mapping and production-tested transactions for **all** tables; inventory alone is not migration evidence |
| Neon schema portability start | **Offline nine-table DDL preview passed PR #30 and merged-main CI 43215433909; no Postgres execution** | Port every additional table, build tested PostgreSQL data adapter/migrations, verify row parity and isolation, encrypted backups and actual hosted restore; no live migration performed |
| Initial hosting design chosen (without provisioning) | **Planned: separate $7 Render Starter plus free Neon; no charge or deployment authorized** | Verify billing workspace/region, safe PostgreSQL migration, encrypted backups/restore, staging identity and tenant isolation; explicitly approve actual service creation and any other costs |
| Offline WSGI public-exposure boundary | **Offline guard passed merged-main CI #43209573560; not a production gateway** | Reject public Host/IP/proxy metadata; build a separate hardened production runtime, enforce network isolation and verify hosted tests |
| Responsive signed-in overview with large cards and deeper details | **Implemented in offline alpha**, not production validated | Mobile browser checks at common Android sizes, focus/keyboard accessibility smoke tests, signed-in shell regression |
| Atomic shared account failure counting | **Offline UPSERT passed merged-main CI #43211450362; not production-level abuse protection** | Add production atomic admission, authenticated ingress, device/IP/global abuse controls, shared durable storage and hosted negative tests |
| Password sign-in, business switching, logout, and role restrictions | **Offline scaffolding and tests** | Correct session expiry, revocation, role-change and current-tenant isolation under an actual hosted trusted identity service |
| Read-only social connection metadata and analytics revocation | **Verified offline concurrency, not connected to actual social APIs** | Internal read-capability allowlist, monotonic status/revocation, transaction-time permission recheck, separate-client races; still requires trusted OAuth, vault, real platform data, token lifecycle and app review before Beta |
| Sponsored AI projected spending and request ceilings | **Offline atomic counts/estimated cost reservations, operator pause and stale-role/funding checks verified; no paid provider activation** | Atomic per-user/tenant/operator request-count accounting, denied reservations roll back, role checks and mid-month cap tests; still needs real operator-approved USD spend ceiling, provider-token usage reconciliation and hosted storage before paid AI |
| Opt-in owner invitation issuance UI/API | **Offline implementation verified; disabled by default and no real delivery** | Must separately enable a trusted delivery callback, backend issue switch and browser control; test role/session isolation, no bearer secret leakage, duplicate recipient conflict and logout safety before hosted Beta |
| Atomic invitation redemption and concurrent clients | **Transactional one-use redemption and multi-client races verified offline** | One-use token claim, current owner/identity recheck and audit insertion share one SQLite write transaction; verify file-backed duplicate/cancel/redeem races and rollback before hosted Beta |
| Owner-only invitation activity audit | **Offline metadata implementation verified (CI 43122286878), not hosted** | Trusted state transitions, bounded GET, strict response validation and tenant isolation; do not backfill invented past events, require hosted tests and provider-backed invite delivery for Beta |
| Owner-private pending invitation cancellation | **Opt-in offline only; no email delivery activated** | Current-role owner session, one-use no-token list/cancel, duplicate/member checks, logout-race regression; requires separately trusted delivery callback and real hosted acceptance testing before beta |
| Verified password/Google-only invitation acceptance | **Gated offline identity and HTTP-style tests verified; not a public enrollment service** | Requires existing verified BAM identity, delivered one-use token, password or trusted nonce-verified Google proof, shared credential throttle, no automatic session, and cross-tenant denial; production needs email delivery, IP/global rate limits and hosted tests |
| Non-executable private calendar readiness digest | **Implemented offline, no publish jobs** | Reports held calendar items, stale draft and manual time blockers; final approval and direct social publishing still unavailable |
| Existing-member team management | **Implemented offline, not hosted** | Owner-only roster, revision-checked role/deactivation, scoped session revocation and owner-private activity history; verify behavior with real accounts and devices before Beta |
| Two-client collaboration & persistence | **File-backed local integration verified, not hosted** | Two authenticated independent gateways, shared drafts, stale writes and role-revocation after restart tested; still requires actual hosted multi-device and backup/restore exercises |
| Local SQLite snapshot/restore | **Ephemeral offline regression verified; not a backup service** | Consistent temporary snapshots and SQLite integrity checked; requires encrypted off-site production backups, retention and a deployment-specific restore drill |
| Held draft creation and copy revisions | **Implemented offline** | Create/edit/resume/review with two simultaneous editors and stale-revision conflict |
| Concurrent held calendar proposal writes | **SQL-level CAS and multi-client races verified offline** | Current draft revision and held status checked atomically with proposal update; version token and unique business/UTC slot enforced across separate SQLite clients, never executable post jobs |
| Draft priority and read-only calendar proposals | **Implemented offline** | No duplicate slots, cross-business separation, timezone/DST correction and no accidental scheduling |
| Private review-feedback notes, change history, readiness summaries | **Implemented offline** | Audit metadata consistency, note permissions and unapproved status after every change |
| Private media preview/receipt | **Pending-only, optional local quarantine** | No storage path exposure, verified file signature and size checks; discarded upload no longer visible |
| Safe AI business facts, targeted drafts, and cost planning | **Offline architecture** | Owner-confirmed facts, isolated personal memory and quota simulation, prompt/response strictness |
| Automated test and migration stability | **Five recent PRs passed exact merged-main CI; latest synchronized main/dev SHA `427566c6` passed Actions `43175777320`; this documentation-only follow-up still needs CI** | Full Python and browser suite **green for the exact release candidate SHA**, restore-from-backup/migration simulation, complete test log |
| Non-production risk/threat walkthrough | **In progress** | Tenant role swaps, stale sessions, duplicate requests, reflected HTML, no hard-coded credentials, no external side effect under failure |

## B. Requirements for a useful private beta (not yet complete)

The private beta should support the full human-supervised workflow for at least two isolated user/business accounts **and multiple team members collaborating within one business** across different devices: sign in, choose the correct business, compose/plan content, review facts and media, edit with conflict detection, preserve the draft, enforce role-specific permissions, and see accurate publishability state. It must **not** imply that merely having a calendar proposal or complete media automatically approves or posts anything.

Before opening a hosted private beta, independently verify:

1. **Trusted identity and persistence:** production-grade credential/session handling, configured Google token verification, TLS/origin restrictions, **SQLite-to-Neon PostgreSQL migration**, backups/restore and secrets management on an approved **separate Render Starter + Neon Free** setup. The selected $7 base target is not a hard cap or a deployment authorization.
2. **Business isolation:** two live accounts cannot enumerate or mutate each other's drafts, metadata, contacts, AI memories, media or connections; role changes take effect without old-token privilege leakage.
3. **Real media safety:** private object storage; trusted malware/media scanning; explicit consent and rights checks; no URL or asset may be treated as verified based solely on client claims.
4. **AI operating policy:** explicit provider/key choice, cost and usage caps approved by the owner, no fallback to an unauthorized paid API, grounded fact checks and user-editable content.
5. **Direct social providers and publication:** official Meta OAuth/Page integration first (without Metricool dependency), current provider permission verification and revocation, owner approval receipt and an *explicitly separately authorized* publish/schedule switch; idempotency/retry and audit controls, including an emergency disable. Smart analytics must use available, provenance-labeled first-party data and never pretend offline sample metrics are live.
6. **Usability and reliability:** real Android-size testing, keyboard and screen-reader checks, offline/error copy, stale-editor recovery, session expiry, backup restore and deployment rollback exercise.

**Additional unverified session hardening:** invitations, scheduling-settings and TruthGuard facts now require matching current-role sessions, with role-promotion regression tests at code commit `4fc1a648`; GitHub Actions remained queued when recorded.

## C. Non-negotiable safety assertions

- A generated draft is **not** an approved post.
- Complete draft media is **not** a trusted safety scan or grant to publish.
- A proposed calendar date is **not** an executable job.
- A stored or manually supplied API key is **not** permission to use it for paid traffic.
- A social connection's existence is **not** permission to post.
- Cross-business requests, stale auth/role sessions, and outdated draft revisions must fail closed.
- Each business must remain usable without Metricool; core direct API publishing may only use capabilities approved by the destination platform.
- Beta and public release dates remain **undecided**. No readiness percentages or invented live analytics should be reported.

## D. Current verification continuity

The offline Alpha source checkpoint `5d80f58c7896fa73965ff6e8c3081af07410188f` passed the full [GitHub Actions 43139361336](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43139361336) suite. The last verified merged `main` checkpoint is `75abc830` via [Actions 43138740119](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43138740119). Documentation updates must pass their own exact-head run and PR review before promotion. None of these results substitutes for real hosted security, provider approval, paid AI consent, or publication authorization.

## Repository sync completed (November 11, 2026)

The offline Alpha source tree and original `main` branding history were merged through [PR #2](https://github.com/BelenosCreations/belenos-marketing-automation/pull/2). Merged source commit `f774564d` passed [full GitHub Actions run 43100795231](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43100795231); the development branch was then fast-forwarded to the same SHA. Recovery references preserve green and pre-merge snapshots. This removes source-control divergence **but does not satisfy private-beta hosting, identity, media-scanning, AI-cost, social publishing, or live integration gates**.

Earlier 'CI pending' statements elsewhere in this document record historical preparation status; the merged code checkpoint is now verified. The documentation updates themselves require a new exact-SHA verification.


## Operator pause and budget holds (offline Alpha)

An internal persistent operator pause now blocks new BAM-sponsored reservation attempts across SQLite clients, with generic, validated hold messages through the explicit-action draft interfaces. Code `cb23ebbd` passed [GitHub Actions 43142566744](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43142566744). It **does not interrupt in-flight provider execution**, trigger a payment/usage alert, or constitute a production emergency stop. Private beta approval still requires an independently enforced provider-dispatch halt, vault/credential controls, operator-approved spending and billing reconciliation.

## Trusted usage-event idempotency (offline Alpha)

An optionally keyed AI cost ledger can now reject duplicate or conflicting trusted usage events, with per-business isolation and lossless migration of earlier events. `9765961f` passed [GitHub Actions 43143316508](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43143316508). Real Beta still requires consistent provider request identity wiring, signed/trusted usage, reconciliation of all reservations against real receipts, provider pricing verification and safe limits on paid traffic. No actual provider invoices have been reconciled.

## Mandatory pre-dispatch OpenAI guard (offline Alpha)

An enabled transport now requires a trusted operator guard, checked before resolving a key and again before the HTTPS opener; negative/missing/error states deny dispatch. The offline `SponsoredAIQuota` exposes a trusted guard reflecting the durable operator pause. Code `d14bbd3f` passed [GitHub Actions 43144166053](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43144166053). This is **not** a guarantee of atomic network cancellation or actual billed-spend enforcement. Private beta still requires operator-approved provider access, worker fencing, credential vault, verified prices, billing reconciliation and deployment security tests.

## Provider response identity and estimated cost events (offline Alpha)

The simulated Responses execution boundary now derives a per-response private usage reference and passes it to the scoped, deduplicating estimated-cost ledger. Missing or malformed IDs fail closed, reused IDs with conflicting counts are refused, and cross-business isolation is tested. Code `f95f0820` passed [GitHub Actions 43145005354](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43145005354). This is **not verified provider billing**, a complete reservation-to-receipt ledger, or a real OpenAI activation. Beta still requires independent reconciliation and owner-approved paid API pricing/credentials.
