# BAM development continuity checkpoint

**Unverified additional Neon portability slice:** `neon_scoped_queries.py` adds pure parameterized SQL for tenant-scoped held drafts and calendar proposals with same-statement active identity/member checks and test-only SQLite query execution. Requires exact-head CI. These are not hosted API endpoints, no real Neon DB driver and no live publishing.

**New verified starting baseline:** PR #31 merged at `2615a0ac18bb70177a971f23a09a9bf0abb01e51`, [merged-main CI 43216601082](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43216601082) **success**, and development fast-forwarded without force.

**Current unverified work:** private offline Neon relational/integrity preflight with no data export. Must pass exact branch and PR CI and merge to main with successful merged-main CI before development sync. No hosted PostgreSQL, app deployment, invoice or authorized paid services.

**Verified previous milestone:** PR #30 merged at `1934a4dd183a261cf2561da025fa383087acc852` and [merged-main GitHub Actions 43215433909](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43215433909) **success**. Development synchronized without force.

**New unverified work:** all-table local SQLite metadata inventory for Neon migration backlog, no user data or SQL text. Resume by checking exact SHA CI and merging via PR. Additional PostgreSQL read/query adaptation, transactional and identity tests are still needed. No hosted services have been created or paid.

**Latest verified release before this candidate:** PR #29 merged at `29e4734fd32d5821a7b7cd4d7a8046cd47bcf959`, [merged-main Actions 43213753494](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43213753494) **success**; development was non-force fast-forwarded to the same commit.

**Current offline candidate (unverified):** first nine-table Neon PostgreSQL DDL preview, SQLite compatibility and privacy-safe inventory, roadmap and regressions. Not a data migration, no PostgreSQL driver or schema executor and no hosted database. Need exact-head branch and PR CI; merge green PR; verify merged-main CI; then fast-forward development. After that continue the remaining schema inventory and transactional adaptation without paid service approval.

**Verified development baseline entering the hosting decision (November 12, 2026):** `main` and `development/phase-3-5-account-directory` synchronized at `2321a19bc4f683aa88fa89b115e3df20106ac071`, [full main CI 43211450362](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43211450362) **success**, after PR #28. Prior PR #27 merged at `f0f8c9d7`, [CI 43209573560](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43209573560) **success**.

**Current planning milestone pending GitHub review and exact-head CI:** owner selected new separate $7/month base Render Starter and independent Neon Free PostgreSQL for BAM private-beta *design only*. No Render service, Neon database, key, domain, provider connection, paid subscription or public endpoint was created or activated. The checked-in planning contract and CI tests affirm all activation flags are false; it is not an operational spend cap. Database migration, media, backup, monitoring, authentication and scheduler still require engineering. Continue development branch → green exact-head PR CI → merge main → green main CI → fast-forward development, never force push.

**Verified starting state (November 12, 2026):** `main` and `development/phase-3-5-account-directory` were synchronized at `f0f8c9d71e81f4b32e69c065ed81850e5001e363`; [merged-main Actions 43209573560](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43209573560) completed **success**, after PR #27.

**Active candidate, not yet merged:** Atomic shared-account login failure UPSERT, timestamp hardening and two-client concurrency regressions at `dbd5b7fb135d00bbcccdae63db4965c1dc43b395`, followed by this documentation commit. Exact-head CI, reviewed PR, merged-main CI and safe non-force fast-forward of development are required. Resume from last verified commit if interrupted.

**Important limit:** This prevents lost failed-attempt counts but not a check/authentication race, brute-force traffic across many IPs/accounts, or credential stuffing at a hosted ingress. Separate production runtime/abuse controls and explicit owner hosting approval remain mandatory. No external services, live social publishing or paid AI authorized.

**Verified start, November 12:** `main` and `development/phase-3-5-account-directory` both `a6dd63bf3af1d2940090594df35fddab1c14489c`; [merged-main CI 43176450765](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43176450765) passed, after reviewed PR #26.

**Current milestone pending verification:** loopback-only offline WSGI network-context guard, tests and `PRIVATE_BETA_INFRASTRUCTURE.md`. Verify exact SHA CI, PR merge, merged-main CI, then fast-forward development without force. Stop before any hosted service purchase, social publishing or paid AI; seek owner approval and budget.


## Authoritative recovery status — November 12, 2026

- **Private repository:** `BelenosCreations/belenos-marketing-automation`.
- **Latest fully verified baseline:** `main` and `development/phase-3-5-account-directory` synchronized at `427566c610bbbcc03b78b4a436746f9832410638`, [successful merged-main Actions 43175777320](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43175777320).
- **Reviewed and merged this development session:** PRs #21, #22, #23, #24 and #25. Each exact PR code and merged-main SHA passed the full offline Python/JavaScript test workflow.
- **This documentation-only follow-up:** changes README, CHANGELOG, DEVELOPMENT_CONTINUITY, DEVELOPMENT_MILESTONES and ALPHA_BETA_READINESS. It must pass its own CI and merge to main before its newer SHA can be marked fully verified. If interrupted, resume from the last green baseline above.
- **Current stage:** private **offline alpha**, no production backend or public signups. Existing trusted team invitations, Google/password acceptance, AI checks and calendar readiness are implemented only in gated/offline test paths. No email transport, hosted verified Google OAuth, live Meta Page connection, publisher worker, automatic social posts, real paid OpenAI requests or Android APK.
- **Next authorization gate:** Owner must separately approve any public/private hosted setup, credential vault, hosting and recurring cost; direct official platform integration (not Metricool) is the planned next production track.
- **Recovery rules:** never force-push, verify CI for each exact commit, merge reviewed green PR to main, verify main CI, then fast-forward development. Historical notes below are preserved as development history and may have old "pending/unmerged" wording.

**Fourth verified merge November 12:** PR #24 merged at `b81430bcd3496d2504a2651534e6fa726eb781a7`; full merged main Actions `43174989252` passed, and development was fast-forwarded without force.

**New unverified development batch:** Private held-calendar readiness digest, authenticated GET-only, with real draft/time consistency indicators but permanent no-publication blockers. New code/test/docs require exact-head CI and reviewed PR; no real schedule worker or provider publishing.


**Third verified merge November 12:** Google-only invitation API groundwork PR #23 merged to main at `39b3c04f31b8c2fc91b0348bf36d658cf4bcbff7`. Full Actions `43174049448` passed; development fast-forwarded to the exact merge commit.

**Unverified current feature batch:** `BAMInvitationAcceptWSGI`, independent offline gateway acceptance opt-in, and direct-call HTTP-style e2e regressions. Source plus README/CHANGELOG/milestones are staged in a new development commit requiring exact-head GitHub CI and reviewed PR. No production HTTP enrollment, email delivery, hosted service or publishing has been enabled.


**Second verified merge November 12:** Invitation redemption and admission guard PR #22 merged at e24a2b3e46ec924c19a0e8b5e4ea6affd3419dff; full main Actions 43172997850 passed. Development was fast-forwarded without force.

**Current unverified development batch:** Non-session verified Google identity lookup plus nonce-verified internal Google invitation redemption; awaiting exact-head CI. No new public route, live external service or paid API.


**Current unmerged development continuation:** An AuthLoginAPI internal invitation redemption gate now requires explicit activation plus trusted persistent login throttling, and returns membership only (no session). New source and tests need exact-head GitHub Actions before review/merge. No network endpoint, new signup or email verification flow was enabled.


**November 12 verified merge:** PR #21 merged at c8a48f359789f0ee63b601c9ba51a3beb74267df; Actions 43171790537 passed the exact merged main commit. The development branch was safely fast-forwarded to the same commit without force. Recovery is available from prior Git references.

**Current development batch:** Verified-password invitation redemption for an existing email-verified identity without initial business membership. The backend remains internal-only, with no public acceptance route or email delivery. Await exact-source GitHub Actions and reviewed PR before merging this new work.


**Verified starting point (November 12, 2026):** `main` `a443097752586f9835086668fdb0eb89b48eeaa2` passed [Actions 43145414577](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43145414577), and development `6506d8ca84d53e2a1aa6013064c65dabf6237ceb` passed [Actions 43145613961](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43145613961). Main was only one commit behind development before this batch.

**New code milestone, awaiting exact-head verification:** `93caf1ab18a6adf299ccffc42da1012699b91e3c` tightens offline sponsored-AI request/response boundaries and adds regressions. The subsequent documentation commit needs its own full CI. Develop only on `development/phase-3-5-account-directory`; merge green milestones to `main` through a PR and fast-forward development after successful main CI. Do not enable paid OpenAI, external OAuth, public deployment or publishing.


**Date:** November 11, 2026 (America/New_York).
**Repository:** `BelenosCreations/belenos-marketing-automation` (private).
**Active development:** `development/phase-3-5-account-directory`.
**Most recent verified `main` commit:** `75abc83000655a37dd234b026bb606c4415d5a3d`, [full CI 43138740119](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43138740119) **success**, merged [PR #15](https://github.com/BelenosCreations/belenos-marketing-automation/pull/15).
**Most recent verified development code:** `5d80f58c7896fa73965ff6e8c3081af07410188f`, [full CI 43139361336](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43139361336) **success**. This documentation-only checkpoint is a newer commit requiring its own run before PR merge.
**Activation status:** Offline private Alpha. No live Meta OAuth, social scheduling/publishing, production hosting, real email invitation delivery, actual OpenAI API calls, paid AI, or public Android APK.
**Recovery refs:** `checkpoint/alpha-last-green-2026-11-11`, `checkpoint/alpha-ci-green-2026-11-11`, `checkpoint/alpha-pre-merge-2026-11-11`, `checkpoint/alpha-team-invitations-2026-11-11`. These are GitHub refs, not enforced branch protection or off-GitHub backups.

**Most recent verified merged baseline:** `ebf71f4cd4afa937a4b1fdc680e4da5d6d2b9c9f` on `main` and development, [Actions 43139924986](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43139924986) and [43140139936](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43140139936) **passed**.
**New verified development code:** `cb23ebbd212986e72e6351b34c834fc3fd43a12c`, [GitHub Actions 43142566744](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43142566744) **passed**. This operator pause/budget-hold milestone has **not yet been merged into main**. The documentation-only checkpoint requires its own exact-SHA CI before a reviewed PR.
**Recovery and safety:** Continue on `development/phase-3-5-account-directory`, never force push, merge green milestones through PR and fast-forward development after green main CI. Paid OpenAI, direct social publishing, public hosting and deployed subscription billing remain disabled.

**Latest verified `main` checkpoint:** `6f6bac7e990f1959d83160d32b9d5a4568c53566`, [GitHub Actions 43143027275](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43143027275) **passed**. Development was fast-forwarded to this merge before the next milestone.
**Most recent verified development source:** `9765961fc8a63433863c91c9700f80891a9544fb`, [GitHub Actions 43143316508](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43143316508) **passed**. Optional hash-based AI usage report deduplication is committed but **not yet merged into main**. This document-only follow-up must pass CI on its own SHA.
**Persistent protections:** Main and development remain GitHub-backed with recovery refs. The new AI operator pause is quota-admission only; cost-event deduplication remains internal and is not billing-provider reconciliation, a paid dispatch switch or production hosting.

**Most recent verified merged `main` commit:** `03484424884a378976dc6cc0d44ff69f0aa75d5d`, [GitHub Actions 43143688135](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43143688135) **passed**. Development was fast-forwarded to the merge before starting this milestone.
**New verified development code:** `d14bbd3f1857d73777a6ec8b958ac0b474a2a1d6` passed [GitHub Actions 43144166053](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43144166053). Mandatory offline OpenAI dispatch guard checks are committed but **not yet merged into main**. This docs-only checkpoint must pass its own CI.
**Safety:** Even with a quota pause and transport preflight, a newly activated pause cannot atomically cancel a concurrent network send already past its final check. Production provider transport remains disabled by default; no paid OpenAI, social publishing or hosting was activated.

**Latest verified `main` checkpoint:** `2d491c0c9e2425021cbc2394614acee591aa744e`, [full main Actions 43144758552](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43144758552) **passed**, merged in [PR #19](https://github.com/BelenosCreations/belenos-marketing-automation/pull/19). Development was fast-forwarded to this merge.
**New verified development source:** `f95f0820080ac77600257e0ea072a0d0c0af3fa3`, [GitHub Actions 43145005354](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43145005354) **passed**. Provider-response identity is connected to the optional local estimated-cost deduplication observer, with fake-transport tests only. Not yet merged to `main`; the following documentation-only SHA requires its own CI.
**Provider/financial safety:** Real paid OpenAI, token-price verification, invoice reconciliation, encrypted vault, durable worker fencing, social publishing, public hosting and billing remain explicitly **disabled or pending separate authorization**. A rejected/invalid response does not prove the provider was not billed.

## Most recent development milestone

- Sponsored request-count and operator-estimated micro-USD quotas are atomic across the individual, business, and BAM operator. Unpriced historical requests prevent accidental mid-month cost undercounting.
- After initial preflight, funding mode and active role are **rechecked under the SQLite writer lock**; business-role demotion and switching to personal-key mode cannot slip through a sponsored quota write.
- `conservative_request_cost_micro_usd` calculates upward-rounded projections **only** from operator-configured pricing and assumed input/output token ceilings. It does not verify model pricing, actual token usage, or provider charges.
- Future trusted composition can use `reserve_current_utc_month` to derive billing month from server time. The legacy explicit-month reservation interface remains **internal/offline**; never let a browser choose its funding month.
- Code at `5d80f58c` passed full [Actions 43139361336](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43139361336). Complete exact-head CI, reviewed milestone PR, green `main` CI, then fast-forward development.

## Safe resume and synchronization procedure

1. Read current `main` and development GitHub HEADs and Actions. Do not assume an interrupted commit or CI run succeeded.
2. Continue work on the development branch with expected-SHA, non-force updates. Keep all data tenant-scoped and fail closed on stale sessions, approvals, and revisions.
3. Update README for current product/implementation, CHANGELOG for changes, DEVELOPMENT_MILESTONES for technical history, and this file for the current recovery checkpoint.
4. Merge at significant **green** milestones (or before ~50 commits of divergence), through a reviewed PR. Verify the exact PR commit, recheck branch heads, merge, verify `main` CI, then fast-forward development to the verified merge.
5. Never activate deployment, provider OAuth, invitation email, paid OpenAI, live scheduling, social publication, or external file transfer without the separate owner-approved production gate.

Older technical milestones and historical run evidence remain in [DEVELOPMENT_MILESTONES.md](DEVELOPMENT_MILESTONES.md) and [CHANGELOG.md](CHANGELOG.md); those are not claims that any earlier pending step is still pending now.

## Product-direction checkpoint — 2026-11-11 (documentation only)

The owner clarified that BAM is being built to **eliminate the need for Metricool**, not to require an external scheduler. The approved core architecture uses **direct, official provider integrations**, with eligible Facebook business Pages first. BAM will own scheduling, publication history, read-only provider analytics and eventually evidence-based Smart recommendations. Provider OAuth, app permissions, token storage and live publication remain **unimplemented and unauthorized**; existing offline social metadata must not be misrepresented as an active connection.

The README was rewritten as the authoritative **product overview** and `PRODUCT_PLAN.md` now contains the implementation sequence and acceptance gates. It also records same-business employee collaboration, a shared multi-tenant backend, optional manual ChatGPT artwork handoff, OpenAI-only BAM-sponsored generation by default and optional securely stored personal API key. Avoid inventing subscription/seat prices, quotas or a dedicated per-employee server. The detailed historical phase log stays in `DEVELOPMENT_MILESTONES.md`, and actual change history stays in `CHANGELOG.md`.

**Branch discipline (current):** develop on the active development branch, merge meaningful green milestones by reviewed PR into `main`, then fast-forward development. Preserve recovery references, avoid force pushes, and stop further divergence before roughly 50 commits. No CI success authorizes deployment, paid AI, direct social publication, or real media verification.


## Main-branch reconciliation candidate — 2026-11-11

The protected-by-convention development snapshot `f66522a40e2696ca49adb183435d218bf3353beb` is the source for this integration candidate. The `main` baseline `fcb28f7a3f8be8d2edf70bd3dfcabbee90e36214` has three separate historical branding commits. Every introduced branding/Android template/test/tool blob is **byte-for-byte identical** in the development snapshot; the only content differences are the historical `README.md` and `CHANGELOG.md`. This merge candidate retains the latest product-accurate README, preserves the distinct `main` history via a two-parent merge commit, and explicitly records the original branding milestone below.

**Safety:** No real social publishing, OAuth, paid model calls, production hosting or APK build was activated. This branch is a merge candidate only. Merge into `main` only after Actions tests complete successfully at the exact candidate SHA and review confirms no conflicting concurrent changes.

## Safe resume procedure

1. Verify the branch head and most recent full green GitHub Actions run. If a chat froze mid-edit, discard unverified assumptions and compare the branch's actual commits, tests and files before making changes.
2. Continue on `development/phase-3-5-account-directory`. Keep `main` unchanged until a separate review/merge decision.
3. Work in larger useful batches; update README, CHANGELOG and DEVELOPMENT_MILESTONES at verified milestones rather than every small patch. Never commit credentials, customer media, secrets or private session tokens.
4. Preserve strict per-user/per-business access, session invalidation, version-checked draft and calendar changes, non-executable status flags, no spoofed live analytics and no unverified promotional claims.

## What is built and tested

- Email/password and Google sign-in backend scaffolding, verified current membership, multi-business switching, logout and least-privilege business roles (not publicly deployed).
- Mobile-first large-card signed-in HTML UI, Content Studio drafts and revision-safe edits, CSV import, private pending-image quarantine and status, owner-confirmed AI facts and manual image-prompt handoff.
- OpenAI structured/draft and targeted-revision architecture, local zero-API-cost product/service draft templates, AI quotas, privacy and token-cost ledger foundations. Paid external calls remain disabled.
- Owner-configured Manual/Smart posting preferences, DST-safe Manual preview, saved unpublished draft-calendar proposals, read-only suggested slots, and version tokens preventing stale editor date changes.
- Private, GET-only `/api/v1/review-readiness` with content/material verification flags, a deeper Approvals checklist and tests for isolation and fail-closed nonapproval.
- Private, version-checked `GET/PUT/DELETE /api/v1/review-feedback` for owner/manager notes; same notes read-only in Content Studio, stale draft feedback warnings, explicit removal confirmation and business-local filters.
- Transactional private metadata audit for note changes, owner/manager-only history with strict response validation, and redacted Approvals activity details. Past events before installation are not backfilled.
- Content Studio supports explicit held-draft priority at creation, local priority/status/channel/text filtering, and grounded private queue pulse with quick filters. No automatic reprioritization or posting.
- Scheduled dashboard requires an explicit two-step confirmation to save a non-executable proposed date from a suggested slot; stale/conflicting entries fail closed.

## Non-negotiable active limits

No social publishing or true scheduled jobs, public hosting, production OAuth token exchange, external image generation, paid OpenAI traffic, automated approval, or actual verified media-scanning service is authorized or enabled. Existing SQLite composition and WSGI browser test adapter are for isolated local development only. Google sign-in needs real trusted provider verification/configuration before use.

## Current unverified alpha safety batch

## Alpha safety: current-role review sessions and stale-editor protection — 2026-11-11

This offline alpha batch strengthens the places that evaluate or change private content:

- Trusted-attestation editorial **source intake** now requires an active, tenant-bound session with an unchanged current membership role, rather than accepting a token merely because the person also belongs to the target business.
- Native and legacy **approval facades** now similarly reject a stale-role session, including the previously unsafe scenario in which a marketing manager has been promoted to owner but is still using a manager-issued token. These offline approval records are not publication permission.
- Held draft **postpone/unavailable/reopen** controls require the displayed draft revision through the HTTPS and Content Studio browser paths; a stale editor gets HTTP 409 instead of silently overwriting newer content. SQLite status updates use the persisted revision as a compare-and-swap condition.
- Verified-media **attachment references** are now saved with revision compare-and-swap, preventing a concurrent image/permission update from unintentionally erasing another update.
- New Python, browser, HTTPS adapter and integrated offline gateway regressions cover conflicts, stale role grants, business separation and blocked publishing.

**Testing status at documentation time:** latest code commit `800e3277350a13dc172c6a68cf0c52f7362608ee`. GitHub Actions runs for this batch are **queued** without test jobs; these changes are *committed but not yet verified*. The most recent separately confirmed successful workflow is [run 43092809091](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43092809091) at `74e55d53`. Do not merge or deploy while the batch remains unverified. Social publishing, production OAuth and paid AI remain off.

**Alpha acceptance gate:** [ALPHA_BETA_READINESS.md](ALPHA_BETA_READINESS.md) tracks offline achievements, unresolved beta requirements, current verification evidence and no-publishing invariants.

## Additional role-change enforcement: team invites, schedules and TruthGuard — 2026-11-11

A follow-up authorization audit found three more offline service boundaries that consulted the current directory role but did not require the issued session role to match. **Invitation creation/revocation, per-business scheduling settings and owner-only TruthGuard business-fact administration** now use `SessionStore.resolve_current` before evaluating tenant/role permissions. Tests verify that promoting a person to owner never lets an existing viewer/manager token silently acquire those owner powers; a separately issued current-role session is necessary. The change does not send invitations, schedule posts, publish, or approve any external AI call.

**Checkpoint:** code commit `4fc1a6481309318b2c4a34453ccafaaef11a0708`. GitHub Actions remained queued with no assigned jobs at documentation time. Do not record it as verified yet.

**Documentation status:** This continuity record supersedes older date-stamped 'pending CI' notes preserved below for historical context. The code merged on November 11 is fully green at `f774564d`; future additions require their own verification.

## Offline Alpha: existing-member team management — 2026-11-11

Current business owners can privately list existing team members in Settings and change an active non-owner's role or deactivate that membership with **two-step confirmation**. The server derives the business from the current owner session; it does not accept a client tenant claim. Changes compare the member's current revision, atomically invalidate affected business sessions and append an actor/time audit event. An employee's unrelated business memberships/sessions remain untouched. An owner cannot use this feature to change themselves, modify another owner, or grant owner privileges. Reactivation and new-member invitations remain separate, not connected through this interface.

Backend: `team_membership_admin.py`, `bam_team_membership_wsgi.py`, migration-safe `accounts.py`, and the disabled-by-default offline gateway routes `GET /api/v1/team/members` and `POST /api/v1/team/membership`. Browser: `ui/team_members_client.js`, `ui/team_overview_workspace.js`, signed-in shell Team settings. Only verified member email is disclosed to the current business owner, and private roster state is cleared on sign-out/business switching. No live hosting, email delivery, social publishing or paid AI was enabled.

**Code CI:** `38e799dba7df86378c0f89ecb216626df07cfff2` passed [run 43105750364](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43105750364), including **922 Python tests**, JavaScript UI regressions and Python compilation. The following docs-only commit will require an independent green run.

## Alpha milestone — private team access activity (November 11, 2026)

Owners can now inspect a **read-only, latest-30 access-change history** in Settings → Team. Events are persisted with the trusted actor/member identifiers, before-and-after roles, action, revision and server time. The backend derives the current business only from the owner session and applies tenant-scoped SQL filters *before* reading recent events. The HTTPS adapter and JavaScript contract verify exact response fields, descending event IDs, owner-only permissions and `publishing_enabled:false`. No invitation token, password, private media or email is included in activity history; the UI may label a member with their already-authorized roster email.

**Verified source:** `d6a79329d2ed2ed5f7d37114aad557be60d464ab`, [Actions 43107012958](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43107012958) — 924 Python tests, browser regression suite and Python compilation **passed**. Offline Alpha only: no external account or publishing side effects. Release synchronization to `main` will use a reviewed CI-gated PR.


## Durable two-client collaboration simulation — 2026-11-11

The Alpha regression suite now uses **two independently initialized BAM offline gateways and separate SQLite connections to the same file-backed database** to simulate two logged-in people working in one business, alongside a second isolated business. This validates end-to-end authentication, shared held-draft visibility, editor revision conflicts and correct retries. Owner role changes invalidate affected business sessions across both instances but preserve valid access to another business. After a simulated app restart, member roles, access revocation and draft contents remain intact.

This is a **local durability and isolation test**, not hosted multi-device collaboration, a tested production relational database migration or an actual deployed backend. No network communication, social publication or paid calls are performed.

**Verified source:** `17c5b470ba4891714953e993c499e1892a712d66` at [GitHub Actions 43107825592](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43107825592): Python compilation, browser UI suite and **926 Python tests passed**. This documentation checkpoint remains pending its own full CI.


## Offline SQLite snapshot/restore integrity exercise — November 11, 2026

The offline Alpha now has a **temporary-file-only backup/restore regression drill** in `test_offline_sqlite_restore_drill.py`. It uses SQLite's consistent online backup API to snapshot a committed database and restore it into a separately initialized BAM gateway. The test verifies `PRAGMA integrity_check`, independent business draft data, recovery of the original version of a changed draft, hashed session-token storage, and preservation of business-scoped revocations and team audit after restoration. All test databases are removed after each run.

**Critical scope:** This test **does not create or schedule an operational backup**. The ephemeral SQLite snapshots are unencrypted and must never become a production export routine. Future approved hosting still needs encrypted, access-controlled/off-site backups, lifecycle retention, monitoring and real recovery rehearsal with production infrastructure.

**Verified code checkpoint:** `1444094af143eaa40c43402d995319f7921f2407`, [GitHub Actions run 43108646726](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43108646726) — Python compilation, browser UI suite and **928 Python tests passed**. The documentation-only follow-up commit must be verified separately; no external services, publishing or AI spending were activated.


## Candidate next work (no authorization required)

Extend read-only campaign queue summaries, test policy boundaries, and refine small-screen review and media workflows and small-screen UX refinements; improve Android/backend architecture documents and migration tests; extend topic planning and cost-free local previews. Maintain complete zero-publishing and zero-paid-call safety.

## Major decisions requiring user input

Public backend hosting (provider, credentials, persistence, budget and security), Google sign-in provider verification, production media scanning/storage and consent workflow, AI spending limits and real OpenAI activation, social provider OAuth permissions, and any live scheduling/automatic publication all require separate user authorization. Never infer consent from an offline green test.
