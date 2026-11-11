# BAM Alpha → Private Beta Readiness Gate

**Status as of November 11, 2026:** Private, offline **alpha**. This checklist is an acceptance gate, not a claim that release milestones were reached. BAM remains unpublished and has no permission to call social publishing services or paid AI.

## A. Checks that can be developed without production authorization

| Acceptance gate | Current status | Evidence required before marking complete |
| --- | --- | --- |
| Responsive signed-in overview with large cards and deeper details | **Implemented in offline alpha**, not production validated | Mobile browser checks at common Android sizes, focus/keyboard accessibility smoke tests, signed-in shell regression |
| Password sign-in, business switching, logout, and role restrictions | **Offline scaffolding and tests** | Correct session expiry, revocation, role-change and current-tenant isolation under an actual hosted trusted identity service |
| Held draft creation and copy revisions | **Implemented offline** | Create/edit/resume/review with two simultaneous editors and stale-revision conflict |
| Draft priority and read-only calendar proposals | **Implemented offline** | No duplicate slots, cross-business separation, timezone/DST correction and no accidental scheduling |
| Private review-feedback notes, change history, readiness summaries | **Implemented offline** | Audit metadata consistency, note permissions and unapproved status after every change |
| Private media preview/receipt | **Pending-only, optional local quarantine** | No storage path exposure, verified file signature and size checks; discarded upload no longer visible |
| Safe AI business facts, targeted drafts, and cost planning | **Offline architecture** | Owner-confirmed facts, isolated personal memory and quota simulation, prompt/response strictness |
| Automated test and migration stability | **Earlier workflow passed; latest security batch is queued** | Full Python and browser suite **green for the exact release candidate SHA**, restore-from-backup/migration simulation, complete test log |
| Non-production risk/threat walkthrough | **In progress** | Tenant role swaps, stale sessions, duplicate requests, reflected HTML, no hard-coded credentials, no external side effect under failure |

## B. Requirements for a useful private beta (not yet complete)

The private beta should support the full human-supervised workflow for at least two isolated user/business accounts across different devices: sign in, choose the correct business, compose/plan content, review facts and media, edit with conflict detection, preserve the draft, and see accurate publishability state. It must **not** imply that merely having a calendar proposal or complete media automatically approves or posts anything.

Before opening a hosted private beta, independently verify:

1. **Trusted identity and persistence:** production-grade credential/session handling, configured Google token verification, TLS/origin restrictions, database migrations, backups/restore and secrets management on an approved hosting setup.
2. **Business isolation:** two live accounts cannot enumerate or mutate each other's drafts, metadata, contacts, AI memories, media or connections; role changes take effect without old-token privilege leakage.
3. **Real media safety:** private object storage; trusted malware/media scanning; explicit consent and rights checks; no URL or asset may be treated as verified based solely on client claims.
4. **AI operating policy:** explicit provider/key choice, cost and usage caps approved by the owner, no fallback to an unauthorized paid API, grounded fact checks and user-editable content.
5. **Social providers and publication:** scoped OAuth connections and revocation, provider permission verification, owner approval receipt and an *explicitly separately authorized* publish/schedule switch; idempotency/retry and audit controls, including an emergency disable.
6. **Usability and reliability:** real Android-size testing, keyboard and screen-reader checks, offline/error copy, stale-editor recovery, session expiry, backup restore and deployment rollback exercise.

## C. Non-negotiable safety assertions

- A generated draft is **not** an approved post.
- Complete draft media is **not** a trusted safety scan or grant to publish.
- A proposed calendar date is **not** an executable job.
- A stored or manually supplied API key is **not** permission to use it for paid traffic.
- A social connection's existence is **not** permission to post.
- Cross-business requests, stale auth/role sessions, and outdated draft revisions must fail closed.
- Beta and public release dates remain **undecided**. No readiness percentages or invented live analytics should be reported.

## D. Current verification continuity

The latest successful Actions run known at this milestone was [43092809091](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43092809091), at commit `74e55d5393a38fbee663b6ec82e72c4ada01c2ec`. The browser now attempts a tenant-authenticated refresh after a rejected edit so stale content is not reused. This is still awaiting GitHub Actions verification. The subsequent current-role / optimistic-concurrency code batch (through `94e894da3777d14fc3c129c0c7f4685d32e595c2`) is committed but GitHub Actions has not begun executing test jobs. **Do not treat that batch as verified until its exact SHA has a green run.** Resume using [DEVELOPMENT_CONTINUITY.md](DEVELOPMENT_CONTINUITY.md).
