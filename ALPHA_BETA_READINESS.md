# BAM Alpha → Private Beta Readiness Gate

**Status as of November 11, 2026:** Private, offline **alpha**. This checklist is an acceptance gate, not a claim that release milestones were reached. BAM remains unpublished and has no permission to call social publishing services or paid AI.

## A. Checks that can be developed without production authorization

| Acceptance gate | Current status | Evidence required before marking complete |
| --- | --- | --- |
| Responsive signed-in overview with large cards and deeper details | **Implemented in offline alpha**, not production validated | Mobile browser checks at common Android sizes, focus/keyboard accessibility smoke tests, signed-in shell regression |
| Password sign-in, business switching, logout, and role restrictions | **Offline scaffolding and tests** | Correct session expiry, revocation, role-change and current-tenant isolation under an actual hosted trusted identity service |
| Read-only social connection metadata and analytics revocation | **Verified offline concurrency, not connected to actual social APIs** | Internal read-capability allowlist, monotonic status/revocation, transaction-time permission recheck, separate-client races; still requires trusted OAuth, vault, real platform data, token lifecycle and app review before Beta |
| Sponsored AI per-business/operator quota ceilings | **Offline quota and concurrency tests; no paid provider activation** | Atomic per-user/tenant/operator request-count accounting, denied reservations roll back, role checks and mid-month cap tests; still needs real operator-approved USD spend ceiling, provider-token usage reconciliation and hosted storage before paid AI |
| Opt-in owner invitation issuance UI/API | **Offline implementation; pending latest CI; disabled by default** | Must separately enable a trusted delivery callback, backend issue switch and browser control; test role/session isolation, no bearer secret leakage, duplicate recipient conflict and logout safety before hosted Beta |
| Atomic invitation redemption and concurrent clients | **Transactional offline code; expanded tests pending CI** | One-use token claim, current owner/identity recheck and audit insertion share one SQLite write transaction; verify file-backed duplicate/cancel/redeem races and rollback before hosted Beta |
| Owner-only invitation activity audit | **Offline metadata implementation verified (CI 43122286878), not hosted** | Trusted state transitions, bounded GET, strict response validation and tenant isolation; do not backfill invented past events, require hosted tests and provider-backed invite delivery for Beta |
| Owner-private pending invitation cancellation | **Opt-in offline only; no email delivery activated** | Current-role owner session, one-use no-token list/cancel, duplicate/member checks, logout-race regression; requires separately trusted delivery callback and real hosted acceptance testing before beta |
| Existing-member team management | **Implemented offline, not hosted** | Owner-only roster, revision-checked role/deactivation, scoped session revocation and owner-private activity history; verify behavior with real accounts and devices before Beta |
| Two-client collaboration & persistence | **File-backed local integration verified, not hosted** | Two authenticated independent gateways, shared drafts, stale writes and role-revocation after restart tested; still requires actual hosted multi-device and backup/restore exercises |
| Local SQLite snapshot/restore | **Ephemeral offline regression verified; not a backup service** | Consistent temporary snapshots and SQLite integrity checked; requires encrypted off-site production backups, retention and a deployment-specific restore drill |
| Held draft creation and copy revisions | **Implemented offline** | Create/edit/resume/review with two simultaneous editors and stale-revision conflict |
| Concurrent held calendar proposal writes | **SQL-level CAS code tested; expanded races pending CI** | Current draft revision and held status checked atomically with proposal update; version token and unique business/UTC slot enforced across separate SQLite clients, never executable post jobs |
| Draft priority and read-only calendar proposals | **Implemented offline** | No duplicate slots, cross-business separation, timezone/DST correction and no accidental scheduling |
| Private review-feedback notes, change history, readiness summaries | **Implemented offline** | Audit metadata consistency, note permissions and unapproved status after every change |
| Private media preview/receipt | **Pending-only, optional local quarantine** | No storage path exposure, verified file signature and size checks; discarded upload no longer visible |
| Safe AI business facts, targeted drafts, and cost planning | **Offline architecture** | Owner-confirmed facts, isolated personal memory and quota simulation, prompt/response strictness |
| Automated test and migration stability | **Earlier workflow passed; latest security batch is queued** | Full Python and browser suite **green for the exact release candidate SHA**, restore-from-backup/migration simulation, complete test log |
| Non-production risk/threat walkthrough | **In progress** | Tenant role swaps, stale sessions, duplicate requests, reflected HTML, no hard-coded credentials, no external side effect under failure |

## B. Requirements for a useful private beta (not yet complete)

The private beta should support the full human-supervised workflow for at least two isolated user/business accounts **and multiple team members collaborating within one business** across different devices: sign in, choose the correct business, compose/plan content, review facts and media, edit with conflict detection, preserve the draft, enforce role-specific permissions, and see accurate publishability state. It must **not** imply that merely having a calendar proposal or complete media automatically approves or posts anything.

Before opening a hosted private beta, independently verify:

1. **Trusted identity and persistence:** production-grade credential/session handling, configured Google token verification, TLS/origin restrictions, database migrations, backups/restore and secrets management on an approved hosting setup.
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

The latest successful Actions run known at this milestone was [43092809091](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43092809091), at commit `74e55d5393a38fbee663b6ec82e72c4ada01c2ec`. The browser now attempts a tenant-authenticated refresh after a rejected edit so stale content is not reused. This is still awaiting GitHub Actions verification. The subsequent current-role / optimistic-concurrency code batch (through `94e894da3777d14fc3c129c0c7f4685d32e595c2`) is committed but GitHub Actions has not begun executing test jobs. **Do not treat that batch as verified until its exact SHA has a green run.** Resume using [DEVELOPMENT_CONTINUITY.md](DEVELOPMENT_CONTINUITY.md).

## Repository sync completed (November 11, 2026)

The offline Alpha source tree and original `main` branding history were merged through [PR #2](https://github.com/BelenosCreations/belenos-marketing-automation/pull/2). Merged source commit `f774564d` passed [full GitHub Actions run 43100795231](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43100795231); the development branch was then fast-forwarded to the same SHA. Recovery references preserve green and pre-merge snapshots. This removes source-control divergence **but does not satisfy private-beta hosting, identity, media-scanning, AI-cost, social publishing, or live integration gates**.

Earlier 'CI pending' statements elsewhere in this document record historical preparation status; the merged code checkpoint is now verified. The documentation updates themselves require a new exact-SHA verification.

