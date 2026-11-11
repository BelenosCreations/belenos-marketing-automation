# BAM development continuity checkpoint

**Date:** 2026-11-11, America/New_York.
**Repository:** `BelenosCreations/belenos-marketing-automation` (private).
**Active branch:** `development/phase-3-5-account-directory`.
**Most recent verified branch commit:** `74e55d5393a38fbee663b6ec82e72c4ada01c2ec` (Actions run 43092809091 successful).
**Verification:** [GitHub Actions run 43092809091](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43092809091) completed successfully. Earlier [run 43091924513](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43091924513) reported 882 Python tests, 72 JavaScript UI test scripts and compilation passed. New code after `74e55d53` remains unverified while runners are queued.
**Latest unverified code checkpoint:** `94e894da3777d14fc3c129c0c7f4685d32e595c2`. GitHub Actions jobs remain queued; do not assert a green code result or merge/deploy on that basis.

After a rejected draft mutation, Content Studio refreshes the authenticated list; the browser test simulates a 409 stale hold and verifies no optimistic success. This is unverified until CI executes.

**Unverified security changes since the last successful run:** editorial recheck and intake, the native and legacy approval facades, revision-checked held-draft hold actions, and compare-and-swap verified-media references. New Python and browser regression tests are committed. Confirm full Python, UI and compilation suites before updating this checkpoint.

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

## Candidate next work (no authorization required)

Extend read-only campaign queue summaries, test policy boundaries, and refine small-screen review and media workflows and small-screen UX refinements; improve Android/backend architecture documents and migration tests; extend topic planning and cost-free local previews. Maintain complete zero-publishing and zero-paid-call safety.

## Major decisions requiring user input

Public backend hosting (provider, credentials, persistence, budget and security), Google sign-in provider verification, production media scanning/storage and consent workflow, AI spending limits and real OpenAI activation, social provider OAuth permissions, and any live scheduling/automatic publication all require separate user authorization. Never infer consent from an offline green test.
