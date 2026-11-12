# BAM development continuity checkpoint

**Date:** 2026-11-11, America/New_York.
**Repository:** `BelenosCreations/belenos-marketing-automation` (private).
**Active branch:** `development/phase-3-5-account-directory`.

## Current milestone — projected AI budget containment (offline, not actual billing)

The previously verified social-connection/analytics revocation milestone was merged via PR #14 and passed `main` [Actions 43137518752](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43137518752) at `c37b5c90941a03aa545518d70b73d448603ac8b0`; development was fast-forwarded. The new projected-micro-USD sponsored AI quota code at `5dee209bb2df1c9b6bb3afe1470cdd2f69798aea` **passed** [Actions 43138168968](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43138168968). This docs-only checkpoint is still awaiting CI, reviewed PR, merged-main CI and development synchronization. Existing request-count quota policy is preserved; projected dollar values are arbitrary **operator-configured conservative estimates**, not prices, provider usage, or verified invoices. No real paid service or publishing enabled.


## Current milestone — offline social permission fail-closed integration

The last synchronized `main` source checkpoint was `77b5ec718dbc47f9380031e86ab7d5206e1218ee` and is fully green ([Actions 43128287935](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43128287935)). Development has implemented explicit read-only registry scopes, stale-state protection and revocation-aware analytics transaction guards. **Code checkpoint `2bf15248172ed56d78b98ad8d84250b45c6749a3` is verified green** ([Actions 43136954406](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43136954406)); the documentation-only follow-up is pending its own exact-SHA verification and PR. No external Meta/OAuth connection was initiated, and neither publishing nor paid AI is enabled. Resume from actual GitHub branch SHA, not older status notes below. Maintain milestone PR merges and main/dev fast-forward synchronization.

**Most recent verified main code:** `0d91198f1550bd6dcb3b6a03ab74d2df9429b526` ([Actions 43127125367](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43127125367) successful; [PR #12](https://github.com/BelenosCreations/belenos-marketing-automation/pull/12) merged offline calendar proposal concurrency protection).
**Most recent verified development code:** `7d18e5ed789d353416236beb934de08ce334957f` ([Actions 43127670375](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43127670375) passed, includes sponsored quota layers and independent-client race tests). The later mid-month metering change `ef3e3509f273e621d0ad26663d02dd36cba650fa` and this documentation are pending final exact-head verification.
**Verification:** Full GitHub Actions [run 43100795231](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43100795231) completed successfully on the exact merged commit. Integration candidate `748c3a1a` also passed [push run 43100505574](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43100505574) and [PR run 43100515217](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43100515217).
**Merge:** [PR #2](https://github.com/BelenosCreations/belenos-marketing-automation/pull/2) reconciled `main` with development; a two-parent integration history preserved both sets of changes. Development was fast-forwarded to main once the merged commit passed.
**Recovery refs:** `checkpoint/alpha-last-green-2026-11-11`, `checkpoint/alpha-ci-green-2026-11-11`, `checkpoint/alpha-pre-merge-2026-11-11`. These are not off-site backups or enforced protection.

**Source-code status:** The previously pending editorial, draft-concurrency, invitation/scheduling and TruthGuard security tests are included in this verified integration. No production features are thereby authorized. This documentation-only follow-up should be independently checked before declaring its own final SHA verified.


**Latest confirmed development source:** `92d172552a5e63cf48f8ed9ef99bebb1f5114e88` passed [Actions 43120560150](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43120560150), including JavaScript syntax validation, UI regressions, and offline Python tests. [Actions 43120107192](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43120107192) separately passed the repaired invitation workspace syntax. Follow-up logout-race test/documentation is pending exact-SHA verification. `main` remains distinct and the new checkpoint is not yet merged. No hosting or social publishing was enabled.

**Latest verified main checkpoint:** `7662dd2976e6420b73cf6ec825eb7aba1dbdb9ac` ([Actions 43121324700](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43121324700)). **Most recent verified development checkpoint:** `538bb79d874821e406b2521384d3feaad0297c33`, [Actions 43122286878](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43122286878) **passed** all offline tests. This documentation-only status update has not yet been separately verified, and the audit milestone still requires a reviewed merge to main. Recovery checkpoint `checkpoint/alpha-team-invitations-2026-11-11` preserves the preceding verified main milestone.

## Current work — sponsored AI request ceilings (offline)

After synchronizing development to verified main `0d91198f`, the code now supports optional server-controlled **individual, business and operator monthly sponsored request ceilings** using an atomic SQLite reservation, and tracks aggregate usage even before their limits are activated. Privileged draft-creation authorization is required. Offline two-client races verify that concurrent reservations cannot overspend a shared *request-count* ceiling. These protections are not billing, dollar limits, usage-priced invoices, hosted enforcement, model API authorization or live AI. Merge only when exact-head CI is green, then verify main and fast-forward development.

## Current work — concurrent-safe held calendar proposals (offline)

Development has advanced past the verified `main` invitation-issuance merge `9b358717` to strengthen calendar proposals. Proposal creation now verifies the current draft revision/status at SQL write time; an edit requires the exact random proposal token and can never overwrite a concurrent update or draft change. Independent SQLite-client races exercise competing edits and double-booking; the separate work remains a **non-executable dry run**. Merge only after exact-sha green CI and review; then verify `main` and synchronize development.

## Current work — optional invitation issuance (offline)

The owner-confirmed issue route, two explicit server/browser feature switches, and strict request/response contracts are added to the development branch only. They are **disabled by default**, require a callback intentionally provided by trusted offline fixtures, never expose tokens, and still do not implement public acceptance or live email. New WSGI, gateway and browser tests include a two-step confirmation and logout race. Exact-head GitHub CI is required before review/merge. No paid services or publishing activated.

## Current work — transactional invitation acceptance (November 11, 2026)

`main` and development were synchronized at `8945577d4b` after PR #9 and successful main CI. Development then added a single-transaction invitation acceptance flow, followed by independent-file-connection duplicate issuance, double-redemption, cancel-versus-redeem races and audit-failure rollback regressions. **Preserve the separate development branch until exact-head CI passes and the reviewed PR merge succeeds.** No external services have been enabled.

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
